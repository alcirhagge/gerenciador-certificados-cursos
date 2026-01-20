"""
Gerenciador de Certificados
Versão: 3.0 - Refatorado com EasyOCR
Descrição: Sistema robusto para processar certificados PDF, extrair informações
          (nome, curso, duração, data) e organizar arquivos automaticamente.
          Utiliza EasyOCR para melhor precisão e tratamento de erros avançado.
Autor: Alcir Hagge
Data: Janeiro 2026
"""

import os
import re
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from tkinter import filedialog
import tkinter as tk
from typing import Dict, List, Optional, Tuple

# Bibliotecas para processamento de PDF e imagem
try:
    import cv2
    import numpy as np
    from PIL import Image, ImageEnhance, ImageFilter
    from pdf2image import convert_from_path
    import easyocr
    import pandas as pd
except ImportError as e:
    print(f"❌ Erro ao importar bibliotecas: {e}")
    print("\n📦 Instale as dependências:")
    print("pip install opencv-python numpy pillow pdf2image easyocr pandas")
    sys.exit(1)


# ==============================================================================
# CONFIGURAÇÃO DE LOGGING
# ==============================================================================

def setup_logging(output_folder: str) -> logging.Logger:
    """
    Configura sistema de logging para registrar erros e processamento.
    
    Args:
        output_folder: Pasta onde salvar os logs
        
    Returns:
        Logger configurado
    """
    log_file = os.path.join(output_folder, f'processamento_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


# ==============================================================================
# CLASSE: ImagePreprocessor
# ==============================================================================

class ImagePreprocessor:
    """
    Realiza pré-processamento avançado de imagens para melhorar OCR.
    
    Técnicas aplicadas:
    - Conversão para escala de cinza
    - Ajuste de contraste e brilho
    - Binarização adaptativa
    - Remoção de ruído
    - Correção de inclinação (deskew)
    """
    
    @staticmethod
    def preprocess(image: np.ndarray, enhance_contrast: bool = True) -> np.ndarray:
        """
        Aplica pipeline completo de pré-processamento otimizado para OCR.
        
        Args:
            image: Imagem numpy array (BGR ou RGB)
            enhance_contrast: Se deve aplicar equalização de histograma
            
        Returns:
            Imagem pré-processada pronta para OCR
        """
        try:
            # 1. Converter para escala de cinza
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # 2. Upscale se imagem for pequena (melhora OCR)
            height, width = gray.shape
            if height < 1000:
                scale = max(1, 1500 // max(height, width))
                gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            
            # 3. Aplicar CLAHE (Contrast Limited Adaptive Histogram Equalization)
            # Melhor que equalizeHist para preservar detalhes
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            
            # 4. Reduzir ruído com denoise bilateral (preserva bordas críticas)
            # Aumentado para tratamento mais agressivo
            denoised = cv2.bilateralFilter(gray, 11, 100, 100)
            
            # 5. Binarização adaptativa com parâmetros otimizados
            binary = cv2.adaptiveThreshold(
                denoised,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                15,  # Aumentado para melhor adaptação
                3    # Constante aumentada
            )
            
            # 6. Operações morfológicas para limpar ruído e preencher gaps
            kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            kernel_large = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            
            # Fecha pequenos buracos
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_small)
            # Remove pequeno ruído
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel_small)
            # Dilata ligeiramente para melhorar texto fino
            cleaned = cv2.dilate(cleaned, kernel_large, iterations=1)
            
            return cleaned
            
        except Exception as e:
            logging.warning(f"Erro no pré-processamento: {e}. Retornando imagem original.")
            return image
    
    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """
        Corrige inclinação da imagem (opcional, pode melhorar OCR).
        
        Args:
            image: Imagem em escala de cinza
            
        Returns:
            Imagem corrigida
        """
        try:
            # Detecta ângulo de inclinação
            coords = np.column_stack(np.where(image > 0))
            angle = cv2.minAreaRect(coords)[-1]
            
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            # Aplica rotação se necessário
            if abs(angle) > 0.5:  # Só corrige se inclinação significativa
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(
                    image, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
                return rotated
            
            return image
            
        except Exception as e:
            logging.warning(f"Erro ao corrigir inclinação: {e}")
            return image


# ==============================================================================
# CLASSE: OCRExtractor
# ==============================================================================

class OCRExtractor:
    """
    Extrai texto de imagens usando EasyOCR com suporte a múltiplos idiomas.
    """
    
    def __init__(self, languages: List[str] = ['pt', 'en']):
        """
        Inicializa o leitor EasyOCR.
        
        Args:
            languages: Lista de idiomas para reconhecimento
        """
        self.logger = logging.getLogger(__name__)
        self.preprocessor = ImagePreprocessor()
        
        try:
            self.logger.info(f"🔄 Inicializando EasyOCR (idiomas: {', '.join(languages)})...")
            self.reader = easyocr.Reader(languages, gpu=False)  # GPU=False para compatibilidade
            self.logger.info("✅ EasyOCR inicializado com sucesso")
        except Exception as e:
            self.logger.error(f"❌ Erro ao inicializar EasyOCR: {e}")
            raise
    
    def extract_from_image(self, image: np.ndarray, preprocess: bool = True) -> str:
        """
        Extrai texto de uma imagem.
        
        Args:
            image: Imagem numpy array
            preprocess: Se deve aplicar pré-processamento
            
        Returns:
            Texto extraído
        """
        try:
            # Aplica pré-processamento se solicitado
            if preprocess:
                image = self.preprocessor.preprocess(image)
            
            # Realiza OCR
            results = self.reader.readtext(image, detail=0, paragraph=True)
            
            # Junta resultados em texto único
            text = '\n'.join(results)
            
            return text
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair texto: {e}")
            return ""
    
    def extract_from_pdf(self, pdf_path: str, dpi: int = 300) -> str:
        """
        Extrai texto de todas as páginas de um PDF.
        
        Args:
            pdf_path: Caminho do arquivo PDF
            dpi: Resolução para converter PDF em imagem
            
        Returns:
            Texto extraído de todas as páginas
        """
        try:
            self.logger.info(f"  📄 Convertendo PDF em imagens (DPI: {dpi})...")
            
            # Converte PDF para imagens com DPI aumentado para melhor qualidade
            # DPI 400 oferece bom balanço entre qualidade e tempo de processamento
            images = convert_from_path(pdf_path, dpi=400)
            
            all_text = []
            
            # Processa cada página
            for page_num, pil_image in enumerate(images, 1):
                self.logger.info(f"  ⚙️  Processando página {page_num}/{len(images)}...")
                
                # Converte PIL para numpy array
                img_array = np.array(pil_image)
                
                # Extrai texto (sem pré-processamento - piora o OCR)
                text = self.extract_from_image(img_array, preprocess=False)
                
                if text:
                    all_text.append(text)
            
            # Junta texto de todas as páginas
            full_text = '\n\n'.join(all_text)
            
            self.logger.info(f"  ✅ Texto extraído: {len(full_text)} caracteres")
            
            return full_text
            
        except Exception as e:
            self.logger.error(f"  ❌ Erro ao processar PDF: {e}")
            return ""


# ==============================================================================
# CLASSE: TextNormalizer
# ==============================================================================

class TextNormalizer:
    """
    Normaliza e limpa texto extraído por OCR.
    """
    
    @staticmethod
    def normalize(text: str) -> str:
        """
        Normaliza texto removendo problemas comuns de OCR.
        
        Args:
            text: Texto bruto do OCR
            
        Returns:
            Texto normalizado
        """
        if not text:
            return ""
        
        # Remove espaços extras e quebras de linha múltiplas
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        
        # Remove caracteres especiais problemáticos mas mantém acentos
        text = re.sub(r'[^\w\sÀ-ÿ\-:,./]', '', text)
        
        # Normaliza pontuação
        text = re.sub(r'\s*([,.:;])\s*', r'\1 ', text)
        
        # Remove espaços no início e fim
        text = text.strip()
        
        return text
    
    @staticmethod
    def clean_for_filename(text: str, max_length: int = 100) -> str:
        """
        Limpa texto para uso em nomes de arquivo.
        
        Args:
            text: Texto a ser limpo
            max_length: Comprimento máximo do nome
            
        Returns:
            Texto seguro para nome de arquivo
        """
        if not text:
            return "Desconhecido"
        
        # Remove/substitui caracteres inválidos para arquivos
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Remove espaços extras
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Limita comprimento
        if len(text) > max_length:
            text = text[:max_length].strip()
        
        return text or "Desconhecido"


# ==============================================================================
# CLASSE: CertificateDataExtractor
# ==============================================================================

class CertificateDataExtractor:
    """
    Extrai dados estruturados de certificados usando regex tolerante.
    """
    
    def __init__(self):
        self.normalizer = TextNormalizer()
        self.logger = logging.getLogger(__name__)
    
    def extract_all(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extrai todos os campos do certificado.
        
        Args:
            text: Texto extraído do certificado
            
        Returns:
            Dicionário com dados extraídos
        """
        # Normaliza texto primeiro
        normalized_text = self.normalizer.normalize(text)
        
        return {
            'nome': self._extract_name(normalized_text),
            'curso': self._extract_course(normalized_text),
            'duracao': self._extract_duration(normalized_text),
            'data': self._extract_date(normalized_text),
            'status': 'completo' if all([
                self._extract_name(normalized_text),
                self._extract_course(normalized_text)
            ]) else 'incompleto'
        }
    
    def _extract_name(self, text: str) -> Optional[str]:
        """
        Extrai nome do aluno procurando padrão: "[NOME] Data [DIA] de"
        
        Args:
            text: Texto normalizado
            
        Returns:
            Nome encontrado ou None
        """
        try:
            # Padrão testado: procura por "[tudo] Data [dia] de"
            # Captura o texto até a palavra "Data"
            match = re.search(r'([\w\s]+?)\s+Data\s+(\d+)\s+de', text, re.IGNORECASE)
            
            if match:
                name = match.group(1).strip()
                # Remove números extras
                name = re.sub(r'\d+', '', name).strip()
                # Remove múltiplos espaços
                name = re.sub(r'\s+', ' ', name).strip()
                # Remove lixo como "Malaquias" ou nomes de instrutores
                # Mantém as 3-4 últimas palavras antes de "Data" que provavelmente é o nome
                words = name.split()
                if len(words) > 4:
                    # Se tiver muitas palavras, pega apenas as últimas 3-4
                    name = ' '.join(words[-3:])
                
                if self._is_valid_name(name):
                    self.logger.info(f"  🔍 Nome encontrado: {name}")
                    return name
            
            self.logger.warning("  ⚠️  Nome não encontrado")
            return None
            
        except Exception as e:
            self.logger.error(f"  ❌ Erro ao extrair nome: {e}")
            return None
    
    def _extract_name_old(self, text: str) -> Optional[str]:
        """
        Extrai nome do aluno com múltiplos padrões, tolerância a erros OCR e fallback.
        
        Args:
            text: Texto normalizado
            
        Returns:
            Nome extraído ou None
        """
        # Corrige erros comuns do OCR ANTES dos padrões
        text = self._fix_ocr_errors(text)
        
        # Lista de padrões regex (do mais específico ao mais genérico)
        patterns = [
            # Padrão 1: Nome antes de "Data"
            r'([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç\s]+(?:[A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç\s]+){1,4})\s+Data',
            
            # Padrão 2: Nome antes de "Duração"  
            r'([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç\s]+(?:[A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç\s]+){1,4})\s+Dura[çc][ãa]o',
            
            # Padrão 3: Após "Nome:" ou "Aluno:"
            r'(?:Nome|Aluno|Participante):\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç\s]+)',
            
            # Padrão 4: Nome antes de "concluiu"
            r'([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç\s]+)\s+concluiu',
            
            # Padrão 5: Tolerante - qualquer nome com 2+ palavras capitalizadas
            r'(?:^|\n)([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç]+(?:\s+[A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç]+)+)(?:\n|$)',
            
            # Padrão 6: Fallback - primeiras 3-5 palavras capitalizadas
            r'^([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç]+(?:\s+[A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç]+){1,3})',
        ]
        
        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    # Remove números e caracteres extras
                    name = re.sub(r'\d+', '', name)
                    name = re.sub(r'\s+', ' ', name).strip()
                    
                    if self._is_valid_name(name):
                        self.logger.info(f"  🔍 Nome encontrado: {name}")
                        return name
            except Exception as e:
                self.logger.debug(f"Padrão falhou: {e}")
                continue
        
        self.logger.warning("  ⚠️  Nome não encontrado")
        return None
    
    def _fix_ocr_errors(self, text: str) -> str:
        """
        Corrige erros comuns cometidos pelo OCR.
        
        Args:
            text: Texto com possíveis erros de OCR
            
        Returns:
            Texto corrigido
        """
        # Erros comuns: l (L minúsculo) confundido com J, I, 1
        # i (i minúsculo) confundido com l, 1
        # rn confundido com m
        
        corrections = {
            # Nomes comuns corrigidos
            'AJves': 'Alves',
            'AIves': 'Alves',  
            'A1ves': 'Alves',
            'SiJva': 'Silva',
            'Si1va': 'Silva',
            'SiIva': 'Silva',
            'Alclr': 'Alcir',
            'A1cir': 'Alcir',
            'AIcir': 'Alcir',
            'Sllva': 'Silva',
            'S1lva': 'Silva',
            'SIlva': 'Silva',
            'da Si1va': 'da Silva',
            'da SiJva': 'da Silva',
            'Hagge': 'Hagge',  # Normalmente ok, mas padronizar
            'Certlficado': 'Certificado',
            'Cert1ficado': 'Certificado',
        }
        
        for wrong, correct in corrections.items():
            text = text.replace(wrong, correct)
        
        return text
    
    def _is_valid_name(self, name: str) -> bool:
        """Valida se o texto parece ser um nome válido (tolerante)."""
        if not name or len(name) < 5:
            return False
        
        # Palavras que NÃO devem aparecer em nomes
        invalid_words = {
            'curso', 'python', 'java', 'certificado', 'conclusão', 'instrutor',
            'professor', 'completo', 'avançado', 'básico', 'data', 'duração',
            'carga', 'horária', 'udemy', 'desenvolvimento', 'programação',
            'sql', 'javascript', 'excel', 'access'
        }
        
        words = name.lower().split()
        
        # Deve ter 2-5 palavras
        if not (2 <= len(words) <= 5):
            return False
        
        # Não pode conter muitos números
        digit_count = sum(1 for c in name if c.isdigit())
        if digit_count > 2:
            return False
        
        # Não pode conter palavras inválidas
        if any(invalid in name.lower() for invalid in invalid_words):
            return False
        
        # Cada palavra deve ter pelo menos 2 caracteres (mais tolerante)
        if any(len(word) < 2 for word in words):
            return False
        
        return True
    
    def _extract_course(self, text: str) -> Optional[str]:
        """
        Extrai nome do curso procurando padrões comuns:
        - "Curso de [COURSE]" 
        - "[COURSE]: [descricao]"
        
        Args:
            text: Texto normalizado
            
        Returns:
            Nome do curso ou None
        """
        try:
            # Padrão 1: "Curso de Python 3 do básico..."
            match = re.search(r'[Cc]urso\s+de\s+([^\.]+?)(?:\s+(?:com|Instrutor|Instrutores|Número|Carga))', text, re.IGNORECASE)
            if match:
                course = self._clean_course(match.group(1))
                if self._is_valid_course(course):
                    self.logger.info(f"  🔍 Curso encontrado: {course}")
                    return course
            
            # Padrão 2: "SQL: Vá do ZERO..." ou "[TECNOLOGIA]: [descricao]"
            match = re.search(r'((?:Python|SQL|JavaScript|Java|C\+\+|PHP|Excel|Power\s+BI)[^\.]*?)(?:\s+(?:Instrutor|Instrutores|Completo|com|Data))', text, re.IGNORECASE)
            if match:
                course = self._clean_course(match.group(1))
                if self._is_valid_course(course):
                    self.logger.info(f"  🔍 Curso encontrado: {course}")
                    return course
            
            self.logger.warning("  ⚠️  Curso não encontrado")
            return None
            
        except Exception as e:
            self.logger.error(f"  ❌ Erro ao extrair curso: {e}")
            return None
    
    def _clean_course(self, course_text: str) -> str:
        """Limpa texto do curso removendo metadados."""
        # Remove quebras de linha e normaliza espaços
        course = re.sub(r'[\n\r]+', ' ', course_text)
        course = re.sub(r'\s+', ' ', course)
        
        # Remove metadados de certificado
        course = re.sub(r'\b(?:UC-[A-Za-z0-9\-]+|ude\.my/\S+|Udemy|certificado)\b', '', course, flags=re.IGNORECASE)
        course = re.sub(r'Número\s+(?:de\s+)?(?:certificado|referência)[^\w]*', '', course, flags=re.IGNORECASE)
        
        # Remove tudo após "Instrutores"
        course = re.split(r'\s+[Ii]nstrutor(?:es)?\b', course)[0]
        
        # Remove caracteres especiais
        course = re.sub(r'[_*|•]+', '', course)
        course = re.sub(r'^[:\-\s]+|[:\-\s]+$', '', course)
        
        return course.strip()
    
    def _is_valid_course(self, course: str) -> bool:
        """Valida se o texto parece ser um curso válido (mais tolerante)."""
        if not course:
            return False
        
        # Aceitamais variações: 5-300 caracteres (era 10-200)
        if len(course) < 5 or len(course) > 300:
            return False
        
        # Não pode começar com palavras indesejadas
        if re.match(r'^\s*(?:Instrutores|Professor|Data|Dura[çc][ãa]o|Carga|Número|De)\b', course, re.IGNORECASE):
            return False
        
        # Deve conter pelo menos uma palavra com 5+ caracteres ou termo técnico
        words = course.split()
        has_long_word = any(len(word) >= 5 for word in words)
        has_tech_term = any(term in course.lower() for term in [
            'python', 'java', 'sql', 'javascript', 'excel', 'power', 'access',
            'html', 'css', 'react', 'angular', 'node', 'django', 'flask'
        ])
        
        return has_long_word or has_tech_term
    
    def _extract_duration(self, text: str) -> Optional[str]:
        """
        Extrai duração do curso.
        
        Args:
            text: Texto normalizado
            
        Returns:
            Duração em formato "XXh" ou None
        """
        patterns = [
            r'(\d+)\s*(?:horas?|h)\s+(?:no\s+)?total',
            r'[Cc]arga\s+hor[áa]ria\s*(?:de\s+)?(\d+)\s*h?',
            r'[Dd]ura[çc][ãa]o:\s*(\d+)\s*h',
            r'\b(\d{2,3})h\b',
        ]
        
        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    hours = match.group(1)
                    if hours.isdigit() and 1 <= int(hours) <= 999:
                        duration = f"{hours}h"
                        self.logger.info(f"  🔍 Duração encontrada: {duration}")
                        return duration
            except Exception as e:
                self.logger.warning(f"Erro ao aplicar padrão de duração: {e}")
                continue
        
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """
        Extrai data do certificado.
        
        Args:
            text: Texto normalizado
            
        Returns:
            Data formatada ou None
        """
        patterns = [
            # DD de MÊS de YYYY
            r'(\d{1,2}\s+de\s+(?:janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+\d{4})',
            
            # DD/MM/YYYY
            r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})\b',
            
            # Data: formato
            r'Data:\s*(\d{1,2}\s+de\s+[A-Za-zçãõáéíóú]+\s+de\s+\d{4})',
        ]
        
        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    date = match.group(1).strip()
                    if re.search(r'\d{4}', date):  # Valida presença de ano
                        self.logger.info(f"  🔍 Data encontrada: {date}")
                        return date
            except Exception as e:
                self.logger.warning(f"Erro ao aplicar padrão de data: {e}")
                continue
        
        return None


# ==============================================================================
# CLASSE: CertificateProcessor
# ==============================================================================

class CertificateProcessor:
    """
    Orquestra o processamento completo de certificados PDF.
    
    Fluxo:
    1. Extrai texto via OCR
    2. Normaliza e extrai dados
    3. Renomeia arquivo
    4. Registra em CSV
    5. Loga erros
    """
    
    def __init__(self, output_folder: str):
        """
        Inicializa processador.
        
        Args:
            output_folder: Pasta onde os PDFs estão localizados
        """
        self.output_folder = output_folder
        self.logger = setup_logging(output_folder)
        
        # Inicializa componentes
        self.logger.info("🚀 Inicializando componentes...")
        self.ocr_extractor = OCRExtractor(languages=['pt', 'en'])
        self.data_extractor = CertificateDataExtractor()
        self.normalizer = TextNormalizer()
        
        # Armazena resultados
        self.processed_data: List[Dict] = []
        self.failed_files: List[Dict] = []
        
        self.logger.info("✅ Componentes inicializados\n")
    
    def process_single_pdf(self, pdf_path: str) -> bool:
        """
        Processa um único arquivo PDF.
        
        Args:
            pdf_path: Caminho completo do PDF
            
        Returns:
            True se processado com sucesso, False caso contrário
        """
        filename = os.path.basename(pdf_path)
        self.logger.info(f"📄 Processando: {filename}")
        
        try:
            # 1. Extrai texto via OCR
            self.logger.info("  🔄 Extraindo texto...")
            text = self.ocr_extractor.extract_from_pdf(pdf_path, dpi=400)
            
            if not text or len(text) < 20:
                self.logger.warning(f"  ⚠️  Texto extraído muito curto ou vazio")
                self.failed_files.append({
                    'arquivo': filename,
                    'motivo': 'Texto muito curto ou vazio',
                    'timestamp': datetime.now().isoformat()
                })
                return False
            
            # 2. Extrai dados estruturados
            self.logger.info("  🔍 Extraindo dados...")
            data = self.data_extractor.extract_all(text)
            
            # 3. Valida dados mínimos
            if not data.get('nome'):
                self.logger.warning("  ⚠️  Nome não encontrado - marcando como incompleto")
                data['nome'] = f"Aluno_Desconhecido_{int(time.time())}"
            
            if not data.get('curso'):
                self.logger.warning("  ⚠️  Curso não encontrado - marcando como incompleto")
                data['curso'] = "Curso Não Identificado"
            
            # 4. Renomeia arquivo
            new_path = self._rename_file(pdf_path, data)
            if new_path:
                data['arquivo_original'] = filename
                data['arquivo_novo'] = os.path.basename(new_path)
            else:
                data['arquivo_original'] = filename
                data['arquivo_novo'] = filename
            
            # 5. Adiciona timestamp
            data['processado_em'] = datetime.now().isoformat()
            
            # 6. Armazena resultado
            self.processed_data.append(data)
            
            self.logger.info(f"  ✅ Processado com sucesso")
            self.logger.info(f"     Nome: {data.get('nome', 'N/A')}")
            self.logger.info(f"     Curso: {data.get('curso', 'N/A')}")
            self.logger.info(f"     Duração: {data.get('duracao', 'N/A')}")
            self.logger.info(f"     Data: {data.get('data', 'N/A')}")
            self.logger.info(f"     Status: {data.get('status', 'N/A')}\n")
            
            return True
            
        except Exception as e:
            self.logger.error(f"  ❌ Erro ao processar {filename}: {e}", exc_info=True)
            self.failed_files.append({
                'arquivo': filename,
                'motivo': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return False
    
    def process_folder(self, folder_path: str) -> Tuple[int, int]:
        """
        Processa todos os PDFs em uma pasta.
        
        Args:
            folder_path: Caminho da pasta com PDFs
            
        Returns:
            Tupla (sucessos, falhas)
        """
        # Lista todos os PDFs
        pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            self.logger.warning("❌ Nenhum arquivo PDF encontrado na pasta")
            return 0, 0
        
        self.logger.info(f"📁 Encontrados {len(pdf_files)} arquivos PDF")
        self.logger.info("=" * 70 + "\n")
        
        success_count = 0
        fail_count = 0
        
        # Processa cada PDF
        for idx, filename in enumerate(pdf_files, 1):
            self.logger.info(f"[{idx}/{len(pdf_files)}] Iniciando processamento")
            
            pdf_path = os.path.join(folder_path, filename)
            
            if self.process_single_pdf(pdf_path):
                success_count += 1
            else:
                fail_count += 1
            
            self.logger.info("-" * 70 + "\n")
        
        return success_count, fail_count
    
    def _rename_file(self, original_path: str, data: Dict) -> Optional[str]:
        """
        Renomeia arquivo baseado nos dados extraídos.
        
        Args:
            original_path: Caminho original do arquivo
            data: Dados extraídos
            
        Returns:
            Novo caminho ou None se falhar
        """
        try:
            folder = os.path.dirname(original_path)
            
            # Extrai componentes do nome
            nome = self.normalizer.clean_for_filename(data.get('nome', 'Desconhecido'))
            curso = self.normalizer.clean_for_filename(data.get('curso', 'Curso'), max_length=50)
            
            # Extrai ano da data
            year = self._extract_year(data.get('data'))
            
            # Constrói novo nome
            new_filename = f"{nome} - {curso} - {year}.pdf"
            new_path = os.path.join(folder, new_filename)
            
            # Evita sobrescrever arquivos existentes
            counter = 1
            while os.path.exists(new_path):
                new_filename = f"{nome} - {curso} - {year} ({counter}).pdf"
                new_path = os.path.join(folder, new_filename)
                counter += 1
            
            # Renomeia arquivo
            os.rename(original_path, new_path)
            self.logger.info(f"  ✅ Renomeado para: {new_filename}")
            
            return new_path
            
        except Exception as e:
            self.logger.error(f"  ❌ Erro ao renomear arquivo: {e}")
            return None
    
    def _extract_year(self, date_str: Optional[str]) -> str:
        """
        Extrai ano da string de data.
        
        Args:
            date_str: String com data
            
        Returns:
            Ano como string ou ano atual
        """
        if not date_str:
            return str(datetime.now().year)
        
        # Procura por padrão de 4 dígitos (ano)
        match = re.search(r'\d{4}', date_str)
        if match:
            return match.group(0)
        
        return str(datetime.now().year)
    
    def save_results(self):
        """
        Salva resultados em arquivos CSV.
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Salva certificados processados com sucesso
        if self.processed_data:
            success_file = os.path.join(
                self.output_folder, 
                f'certificados_processados_{timestamp}.csv'
            )
            
            try:
                df_success = pd.DataFrame(self.processed_data)
                df_success.to_csv(success_file, index=False, encoding='utf-8-sig')
                self.logger.info(f"📊 Resultados salvos em: {success_file}")
            except Exception as e:
                self.logger.error(f"❌ Erro ao salvar CSV de sucesso: {e}")
        
        # 2. Salva log de arquivos com falha
        if self.failed_files:
            failed_file = os.path.join(
                self.output_folder,
                f'certificados_falhas_{timestamp}.csv'
            )
            
            try:
                df_failed = pd.DataFrame(self.failed_files)
                df_failed.to_csv(failed_file, index=False, encoding='utf-8-sig')
                self.logger.info(f"⚠️  Log de falhas salvo em: {failed_file}")
            except Exception as e:
                self.logger.error(f"❌ Erro ao salvar CSV de falhas: {e}")
    
    def generate_report(self, success_count: int, fail_count: int):
        """
        Gera relatório final do processamento.
        
        Args:
            success_count: Número de sucessos
            fail_count: Número de falhas
        """
        total = success_count + fail_count
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        self.logger.info("\n" + "=" * 70)
        self.logger.info("       RELATÓRIO FINAL")
        self.logger.info("=" * 70)
        self.logger.info(f"Total de arquivos: {total}")
        self.logger.info(f"✅ Processados com sucesso: {success_count}")
        self.logger.info(f"❌ Falhas: {fail_count}")
        self.logger.info(f"📊 Taxa de sucesso: {success_rate:.1f}%")
        
        # Estatísticas adicionais
        if self.processed_data:
            complete_count = sum(1 for d in self.processed_data if d.get('status') == 'completo')
            incomplete_count = len(self.processed_data) - complete_count
            
            self.logger.info(f"\n📋 Dados extraídos:")
            self.logger.info(f"  Completos: {complete_count}")
            self.logger.info(f"  Incompletos: {incomplete_count}")
        
        self.logger.info("=" * 70 + "\n")


# ==============================================================================
# FUNÇÃO: select_folder
# ==============================================================================

def select_folder() -> Optional[str]:
    """
    Abre diálogo para seleção de pasta.
    
    Returns:
        Caminho da pasta selecionada ou None
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    folder = filedialog.askdirectory(title="Selecione a pasta com certificados PDF")
    root.destroy()
    return folder


# ==============================================================================
# FUNÇÃO PRINCIPAL: main
# ==============================================================================

def main():
    """
    Função principal do programa.
    """
    print("=" * 70)
    print("       GERENCIADOR DE CERTIFICADOS v3.0")
    print("       Powered by EasyOCR")
    print("=" * 70)
    print("\n📋 Este programa irá:")
    print("  1. Extrair texto dos PDFs usando EasyOCR avançado")
    print("  2. Aplicar pré-processamento de imagem para melhor OCR")
    print("  3. Identificar: Nome, Curso, Duração e Data")
    print("  4. Renomear: Nome - Curso - Ano.pdf")
    print("  5. Gerar relatórios CSV (sucessos e falhas)")
    print("  6. Criar log detalhado de processamento")
    print("\n⚠️  IMPORTANTE:")
    print("  - Primeira execução pode demorar (download de modelos EasyOCR)")
    print("  - PDFs de baixa qualidade podem ter extração incompleta")
    print("  - Arquivos com falha serão registrados em CSV separado")
    
    input("\n\nPressione ENTER para começar...")
    
    # Seleciona pasta
    print("\n📁 Selecione a pasta com os certificados...")
    folder = select_folder()
    
    if not folder:
        print("❌ Nenhuma pasta selecionada. Encerrando.")
        return
    
    print(f"\n✅ Pasta selecionada: {folder}\n")
    
    try:
        # Inicializa processador
        processor = CertificateProcessor(folder)
        
        # Processa todos os PDFs
        start_time = time.time()
        success_count, fail_count = processor.process_folder(folder)
        elapsed_time = time.time() - start_time
        
        # Salva resultados
        processor.save_results()
        
        # Gera relatório
        processor.generate_report(success_count, fail_count)
        
        print(f"\n⏱️  Tempo total: {elapsed_time:.2f} segundos")
        print(f"⚡ Média: {elapsed_time/(success_count + fail_count):.2f}s por arquivo\n")
        
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")
        logging.error(f"Erro crítico na execução: {e}", exc_info=True)
    
    print("\n" + "=" * 70)
    print("       PROCESSAMENTO CONCLUÍDO!")
    print("=" * 70)
    input("\nPressione ENTER para sair...")


# ==============================================================================
# PONTO DE ENTRADA
# ==============================================================================

if __name__ == "__main__":
    main()
