import os
import sys
import re
import csv
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox


# ============================================================================
# MÓDULO DE VERIFICAÇÃO E INSTALAÇÃO DE DEPENDÊNCIAS
# ============================================================================

def verificar_admin():
    """Verifica se está rodando como administrador"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def solicitar_admin():
    """Reinicia o script com privilégios de administrador"""
    try:
        import ctypes
        
        if verificar_admin():
            return True
        
        print("\n🔐 Solicitando privilégios de administrador...")
        print("   (Uma janela de controle de conta de usuário irá aparecer)")
        
        # Reinicia o script como administrador
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            f'"{os.path.abspath(__file__)}"',
            None,
            1
        )
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Não foi possível solicitar privilégios: {e}")
        input("Pressione ENTER para continuar mesmo assim...")
        return False

def verificar_tesseract():
    """Verifica se Tesseract está instalado e funcionando"""
    try:
        import pytesseract
        
        # Verifica caminho padrão de instalação primeiro
        tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        tessdata_path = r'C:\Program Files\Tesseract-OCR\tessdata'
        
        if os.path.exists(tesseract_path):
            # Configura o caminho
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR'
            
            # Testa se funciona
            try:
                resultado = subprocess.run([tesseract_path, '--version'], 
                                          capture_output=True, text=True, timeout=5)
                if resultado.returncode == 0:
                    return True
            except:
                pass
        
        # Tenta via PATH
        try:
            resultado = subprocess.run(['tesseract', '--version'], 
                                       capture_output=True, text=True, timeout=5)
            if resultado.returncode == 0:
                # Configura caminho se encontrado via PATH
                if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
                    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                    os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR'
                return True
        except:
            pass
        
        return False
    except:
        return False

def verificar_poppler():
    """Verifica se Poppler está disponível"""
    try:
        resultado = subprocess.run(['pdftoppm', '-v'], 
                                   capture_output=True, text=True, timeout=5)
        return resultado.returncode == 0
    except:
        # Verifica caminho alternativo no home do usuário
        poppler_bin = Path.home() / "poppler" / "Library" / "bin"
        if (poppler_bin / "pdftoppm.exe").exists():
            os.environ["PATH"] = str(poppler_bin) + ";" + os.environ.get("PATH", "")
            return True
        return False

def instalar_pacote_python(pacote):
    """Instala um pacote Python"""
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', pacote, '-q'], 
                      check=True, timeout=300)
        return True
    except:
        return False

def verificar_pacotes_python():
    """Verifica e instala pacotes Python necessários"""
    pacotes = {
        'PyPDF2': 'PyPDF2',
        'pdf2image': 'pdf2image',
        'pytesseract': 'pytesseract',
        'PIL': 'Pillow'
    }
    
    faltando = []
    for modulo, pacote in pacotes.items():
        try:
            __import__(modulo)
        except ImportError:
            faltando.append(pacote)
    
    if faltando:
        print(f"\n📦 Instalando pacotes Python: {', '.join(faltando)}...")
        for pacote in faltando:
            print(f"   Instalando {pacote}...", end=" ")
            if instalar_pacote_python(pacote):
                print("✓")
            else:
                print("✗")
                return False
    
    return True

def instalar_tesseract():
    """Baixa e instala Tesseract OCR"""
    print("\n📥 Instalando Tesseract OCR...")
    
    tesseract_path = r"C:\Program Files\Tesseract-OCR"
    if os.path.exists(os.path.join(tesseract_path, "tesseract.exe")):
        print("   ✓ Já instalado!")
        return True
    
    try:
        tesseract_url = "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
        
        print("   Baixando instalador...")
        with tempfile.TemporaryDirectory() as tmpdir:
            installer_path = os.path.join(tmpdir, "tesseract-installer.exe")
            urllib.request.urlretrieve(tesseract_url, installer_path)
            
            print("   Instalando (pode demorar alguns minutos)...")
            resultado = subprocess.run([
                installer_path,
                "/S",
                "/D=" + tesseract_path
            ], timeout=300)
            
            if os.path.exists(os.path.join(tesseract_path, "tesseract.exe")):
                print("   ✓ Instalado com sucesso!")
                
                # Baixa dados de português
                print("   📥 Baixando dados de português...")
                try:
                    tessdata_path = os.path.join(tesseract_path, "tessdata")
                    os.makedirs(tessdata_path, exist_ok=True)
                    
                    por_url = 'https://github.com/tesseract-ocr/tessdata/raw/main/por.traineddata'
                    por_file = os.path.join(tessdata_path, 'por.traineddata')
                    
                    urllib.request.urlretrieve(por_url, por_file)
                    print("   ✓ Dados de português instalados!")
                except Exception as e:
                    print(f"   ⚠ Erro ao baixar dados de português: {e}")
                
                return True
            else:
                print("   ✗ Falha na instalação")
                return False
                
    except Exception as e:
        print(f"   ✗ Erro: {e}")
        return False

def instalar_poppler():
    """Baixa e configura Poppler"""
    print("\n📥 Instalando Poppler...")
    
    poppler_dir = Path.home() / "poppler"
    poppler_bin = poppler_dir / "Library" / "bin"
    
    if (poppler_bin / "pdftoppm.exe").exists():
        print("   ✓ Já instalado!")
        os.environ["PATH"] = str(poppler_bin) + ";" + os.environ.get("PATH", "")
        return True
    
    try:
        poppler_url = "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip"
        
        print(f"   Baixando para {poppler_dir}...")
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "poppler.zip")
            urllib.request.urlretrieve(poppler_url, zip_path)
            
            print("   Extraindo...")
            poppler_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(poppler_dir)
            
            # Reorganiza estrutura
            extracted = [f for f in poppler_dir.iterdir() if f.is_dir() and f.name.startswith('poppler-')]
            if extracted:
                source = extracted[0]
                for item in source.iterdir():
                    target = poppler_dir / item.name
                    if target.exists():
                        import shutil
                        shutil.rmtree(target) if target.is_dir() else target.unlink()
                    item.rename(target)
                source.rmdir()
            
            if (poppler_bin / "pdftoppm.exe").exists():
                print("   ✓ Instalado com sucesso!")
                os.environ["PATH"] = str(poppler_bin) + ";" + os.environ.get("PATH", "")
                return True
            else:
                print("   ✗ Falha na instalação")
                return False
                
    except Exception as e:
        print(f"   ✗ Erro: {e}")
        return False

def verificar_e_instalar_dependencias():
    """Verifica e instala todas as dependências necessárias"""
    print("=" * 70)
    print("VERIFICANDO DEPENDÊNCIAS")
    print("=" * 70)
    
    # 1. Verifica pacotes Python
    print("\n1. Verificando pacotes Python...")
    if not verificar_pacotes_python():
        print("❌ Falha ao instalar pacotes Python")
        return False
    print("   ✓ Pacotes Python OK")
    
    # 2. Verifica Tesseract
    print("\n2. Verificando Tesseract OCR...")
    if not verificar_tesseract():
        print("   ⚠ Tesseract não encontrado")
        print("\n   📝 AÇÃO NECESSÁRIA:")
        print("   1. Baixe Tesseract OCR:")
        print("      https://github.com/UB-Mannheim/tesseract/wiki")
        print("   2. Durante instalação, marque 'Portuguese'")
        print("   3. Execute este programa novamente")
        print()
        
        resposta = input("   Deseja continuar mesmo assim? Alguns certificados podem não funcionar (S/N): ")
        if resposta.lower() not in ['s', 'sim', 'y', 'yes']:
            return False
    else:
        print("   ✓ Tesseract OK")
    
    # 3. Verifica Poppler
    print("\n3. Verificando Poppler...")
    if not verificar_poppler():
        print("   ⚠ Poppler não encontrado")
        
        if not instalar_poppler():
            print("   ⚠ Poppler não instalado (não crítico)")
            print("   Alguns PDFs podem não funcionar")
        else:
            print("   ✓ Poppler OK")
    else:
        print("   ✓ Poppler OK")
    
    print("\n" + "=" * 70)
    print("✅ VERIFICAÇÃO CONCLUÍDA - Sistema pronto!")
    print("=" * 70)
    print()
    
    return True


# ============================================================================
# MÓDULO PRINCIPAL - GERENCIADOR DE CERTIFICADOS
# ============================================================================

class GerenciadorCertificados:
    def __init__(self):
        self.pasta_selecionada = None
        self.certificados_processados = []
        
        # Configura Tesseract
        self.configurar_tesseract()
    
    def configurar_tesseract(self):
        """Configura caminho do Tesseract"""
        try:
            import pytesseract
            tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            tessdata_path = r'C:\Program Files\Tesseract-OCR\tessdata'
            
            if os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                # Configura variável de ambiente CORRETAMENTE
                os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'
        except:
            pass
        
    def selecionar_pasta(self):
        """Abre diálogo para selecionar pasta com certificados"""
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # Traz para frente
        root.lift()
        root.focus_force()
        pasta = filedialog.askdirectory(title="Selecione a pasta com os certificados", parent=root)
        root.destroy()
        return pasta
    
    def extrair_texto_pdf(self, caminho_pdf):
        """Extrai texto de um arquivo PDF (com OCR se necessário)"""
        try:
            import PyPDF2
            
            # Primeiro tenta extração direta de texto
            with open(caminho_pdf, 'rb') as arquivo:
                leitor = PyPDF2.PdfReader(arquivo)
                texto = ""
                for pagina in leitor.pages:
                    texto += pagina.extract_text()
            
            # Se não conseguiu extrair texto, usa OCR
            if not texto or len(texto.strip()) < 50:
                print("  ⚙ Usando OCR para extrair texto...")
                texto = self.extrair_texto_ocr(caminho_pdf)
            
            return texto
        except Exception as e:
            print(f"  ❌ Erro ao ler PDF: {e}")
            # Tenta OCR como fallback
            try:
                print("  ⚙ Tentando OCR...")
                return self.extrair_texto_ocr(caminho_pdf)
            except:
                return None
    
    def extrair_texto_ocr(self, caminho_pdf):
        """Extrai texto usando OCR (para PDFs baseados em imagens)"""
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            # Converte PDF para imagens
            imagens = convert_from_path(caminho_pdf, dpi=300)
            
            # Tenta usar português, senão inglês
            idioma = self.detectar_idioma_tesseract()
            
            texto = ""
            for i, imagem in enumerate(imagens):
                # Aplica OCR em cada página
                texto_pagina = pytesseract.image_to_string(imagem, lang=idioma)
                texto += texto_pagina + "\n"
            
            return texto
        except Exception as e:
            print(f"  ❌ Erro no OCR: {e}")
            return None
    
    def detectar_idioma_tesseract(self):
        """Detecta qual idioma usar no Tesseract (português ou inglês)"""
        try:
            import pytesseract
            
            # Verifica se existe arquivo de português em vários caminhos
            tessdata_paths = [
                r'C:\Program Files\Tesseract-OCR\tessdata',
                os.path.join(str(Path.home()), '.tesseract', 'tessdata')
            ]
            
            for tessdata_path in tessdata_paths:
                por_file = os.path.join(tessdata_path, 'por.traineddata')
                if os.path.exists(por_file):
                    # Configura TESSDATA_PREFIX corretamente
                    os.environ['TESSDATA_PREFIX'] = tessdata_path
                    return 'por'
            
            # Se não encontrou, tenta inglês
            print("  ⚠ Usando inglês (português não disponível)")
            return 'eng'
        except Exception as e:
            print(f"  ⚠ Erro ao detectar idioma: {e}")
            return 'eng'
    
    def garantir_dados_portugues(self):
        """Garante que os dados de português estão instalados"""
        import pytesseract
        import shutil
        
        # Caminhos possíveis do Tesseract
        tesseract_base = r'C:\Program Files\Tesseract-OCR'
        tessdata_path = os.path.join(tesseract_base, 'tessdata')
        por_file = os.path.join(tessdata_path, 'por.traineddata')
        
        # Verifica se existe no caminho principal
        if os.path.exists(por_file):
            print(f"  ✓ Dados de português encontrados")
            os.environ['TESSDATA_PREFIX'] = tessdata_path
            pytesseract.pytesseract.tesseract_cmd = os.path.join(tesseract_base, 'tesseract.exe')
            return
        
        # Procura em subpastas (algumas instalações colocam em Script_Data)
        print("  🔍 Procurando dados de português...")
        for root_dir, dirs, files in os.walk(tesseract_base):
            if 'por.traineddata' in files:
                origem = os.path.join(root_dir, 'por.traineddata')
                print(f"  ✓ Encontrado em: {origem}")
                print(f"  📋 Copiando para: {tessdata_path}")
                try:
                    os.makedirs(tessdata_path, exist_ok=True)
                    shutil.copy2(origem, por_file)
                    print("  ✓ Arquivo copiado com sucesso!")
                    os.environ['TESSDATA_PREFIX'] = tessdata_path
                    pytesseract.pytesseract.tesseract_cmd = os.path.join(tesseract_base, 'tesseract.exe')
                    return
                except Exception as e:
                    print(f"  ⚠ Erro ao copiar: {e}")
                    break
        
        # Se não encontrou, baixa da internet
        print("  ⚠ Dados de português não encontrados na instalação")
        print("  📥 Baixando dados de português da internet...")
        self.baixar_dados_portugues()
    
    def baixar_dados_portugues(self):
        """Baixa arquivo de dados de português para Tesseract"""
        try:
            # Tenta primeiro o caminho padrão
            tessdata_path = r'C:\Program Files\Tesseract-OCR\tessdata'
            por_file = os.path.join(tessdata_path, 'por.traineddata')
            
            # Verifica se tem permissão de escrita
            try:
                os.makedirs(tessdata_path, exist_ok=True)
                # Tenta criar arquivo de teste
                test_file = os.path.join(tessdata_path, '.test_write')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                usa_alternativo = False
            except:
                # Sem permissão, usa caminho alternativo
                usa_alternativo = True
            
            # Se não tiver permissão, usa caminho alternativo no home do usuário
            if usa_alternativo:
                tessdata_path = os.path.join(str(Path.home()), '.tesseract', 'tessdata')
                por_file = os.path.join(tessdata_path, 'por.traineddata')
                os.makedirs(tessdata_path, exist_ok=True)
                # Configura TESSDATA_PREFIX para o caminho alternativo
                os.environ['TESSDATA_PREFIX'] = os.path.join(str(Path.home()), '.tesseract')
                print(f"  ℹ Usando caminho alternativo (sem permissão de admin)")
            
            por_url = 'https://github.com/tesseract-ocr/tessdata/raw/main/por.traineddata'
            
            print(f"  📥 Baixando de: {por_url}")
            print(f"  💾 Salvando em: {tessdata_path}")
            urllib.request.urlretrieve(por_url, por_file)
            print("  ✓ Dados de português instalados com sucesso!")
            return True
        except Exception as e:
            print(f"  ❌ Erro ao baixar dados: {e}")
            print(f"  💡 Tente executar como administrador")
            return False
    
    def extrair_informacoes(self, texto):
        """Extrai informações do certificado (nome, curso, duração, data) - Funciona com múltiplos formatos"""
        if not texto:
            return None
        
        # Mantém texto original e cria versão normalizada
        texto_original = texto
        texto = re.sub(r'\s+', ' ', texto)
        
        info = {
            'nome': None,
            'curso': None,
            'duracao': None,
            'data': None
        }
        
        # ===== EXTRAÇÃO DE NOME =====
        # Palavras que NÃO são nomes de pessoas
        palavras_excluir = [
            'curso', 'python', 'java', 'instrutor', 'professor', 'sql', 'conclusão', 
            'certificado', 'completo', 'avançado', 'básico', 'zero', 'atualizado',
            'luiz', 'otávio', 'miranda', 'tales', 'calogi', 'malaquias', 'javascript',
            'react', 'angular', 'vue', 'node', 'docker', 'kubernetes', 'aws', 'azure',
            'data', 'science', 'machine', 'learning', 'artificial', 'intelligence',
            'workshop', 'treinamento', 'palestra', 'seminário', 'webinar', 'online',
            'presencial', 'ead', 'participação', 'aproveitamento', 'nota', 'carga'
        ]
        
        padroes_nome = [
            # 1. Udemy: nome entre "Instrutores" e "Data"
            r'(?:Instrutores|instrutor)[^A-Z]+?(?:[A-Z][a-záàâãéèêíïóôõöúçñ]+[,\s]+)*?([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+(?:\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+)+)\s+Data',
            
            # 2. Padrão "certifica que" / "certificamos que"
            r'(?:certifica(?:mos)?\s+que|conferido\s+a)\s+([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+(?:\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+)+)',
            
            # 3. Padrão "concluiu" / "participou"
            r'(?:concluiu|participou|compareceu)\s+(?:com\s+sucesso\s+)?(?:o|ao|do)?\s*(?:curso|treinamento|workshop)?\s*[^A-Z]{0,20}([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+(?:\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+)+)',
            
            # 4. "Nome:" ou "Aluno:" seguido de nome
            r'(?:Nome|Aluno|Participante)[:\s]+([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+(?:\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+)+)',
            
            # 5. Nome antes de "Data" (genérico)
            r'\b([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+(?:\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+)?)\s+Data',
            
            # 6. Nome entre certificado e curso (padrão genérico)
            r'certificado[^A-Z]{0,30}([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+(?:\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][a-záàâãéèêíïóôõöúçñ]+){1,4})',
        ]
        
        for padrao in padroes_nome:
            match = re.search(padrao, texto, re.IGNORECASE if any(x in padrao for x in ['certifica', 'concluiu', 'participou', 'Nome', 'Aluno']) else 0)
            if match:
                nome_candidato = match.group(1).strip()
                nome_lower = nome_candidato.lower()
                
                # Validações
                palavras = nome_candidato.split()
                
                # Deve ter 2-6 palavras
                if len(palavras) < 2 or len(palavras) > 6:
                    continue
                
                # Não pode conter palavras excluídas
                if any(palavra in nome_lower for palavra in palavras_excluir):
                    continue
                
                # Não pode ter números
                if any(char.isdigit() for char in nome_candidato):
                    continue
                
                # Deve ter pelo menos 5 caracteres
                if len(nome_candidato) < 5:
                    continue
                
                info['nome'] = nome_candidato
                break
        
        # ===== EXTRAÇÃO DE CURSO =====
        padroes_curso = [
            # 1. Udemy: entre "CERTIFICADO DE CONCLUSÃO" e "Instrutores"
            r'CERTIFICADO\s+DE\s+CONCLUS[ÃA]O\s+(.+?)\s+(?:Instrutores|Data)',
            
            # 2. "Curso de/sobre" ou "Curso:"
            r'[Cc]urso\s+(?:de|sobre|em)[:\s]+([^\n\r]{10,200}?)(?:\s+[Cc]arga|[Dd]ura[çc][ãa]o|[Dd]ata|$)',
            r'[Cc]urso[:\s]+([^\n\r]{10,200}?)(?:\s+[Cc]arga|[Dd]ura[çc][ãa]o|[Dd]ata|$)',
            
            # 3. Workshop, Treinamento, Palestra
            r'(?:[Ww]orkshop|[Tt]reinamento|[Pp]alestra|[Ss]emin[áa]rio)\s+(?:de|sobre|em)?[:\s]*([^\n\r]{10,150}?)(?:\s+[Cc]arga|[Dd]ura[çc][ãa]o|[Dd]ata|$)',
            
            # 4. "Certificado" + título longo (genérico)
            r'[Cc]ertificado\s+(?:de)?\s*([^\n\r]{20,200}?)(?:\s+[Cc]arga|[Dd]ura[çc][ãa]o|[Dd]ata|[Aa]luno|[Nn]ome|$)',
            
            # 5. Entre "conclusão" e data/carga horária
            r'conclus[ãa]o\s+(?:do|de)?\s*([^\n\r]{15,150}?)(?:\s+[Cc]arga|[Dd]ura[çc][ãa]o|[Dd]ata|$)',
            
            # 6. Título em MAIÚSCULAS (geralmente nome do curso)
            r'\b([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑa-záàâãéèêíïóôõöúçñ\s]{20,150})\b(?=\s+[Cc]arga|\s+[Dd]ura[çc][ãa]o|\s+[Ii]nstrutor)',
        ]
        
        for padrao in padroes_curso:
            match = re.search(padrao, texto, re.MULTILINE)
            if match:
                curso = match.group(1).strip()
                
                # Limpeza
                curso = re.sub(r'[_*\|•◦▪▫]+', '', curso)
                curso = re.sub(r'\s+', ' ', curso)
                curso = re.sub(r'^[:\-\s]+|[:\-\s]+$', '', curso)
                
                # Validações
                # Tamanho mínimo e máximo
                if len(curso) < 10 or len(curso) > 200:
                    continue
                
                # Não pode ser só números
                if curso.replace(' ', '').replace('.', '').isdigit():
                    continue
                
                # Não pode ser um nome de pessoa (poucas palavras capitalizadas)
                palavras = curso.split()
                if len(palavras) <= 4 and all(p[0].isupper() and p[1:].islower() for p in palavras if p):
                    continue
                
                # Remove sufixos comuns
                curso = re.sub(r'\s+(?:online|presencial|ead|remoto|virtual)$', '', curso, flags=re.IGNORECASE)
                
                info['curso'] = curso
                break
        
        # ===== EXTRAÇÃO DE DURAÇÃO =====
        padroes_duracao = [
            # Horas totais
            r'(\d+)\s*(?:horas?|h)\s+(?:no\s+)?total',
            r'Total[:\s]+(\d+)\s*(?:horas?|h)',
            
            # Carga horária
            r'[Cc]arga\s+hor[áa]ria[:\s]+(\d+)\s*(?:horas?|h)',
            r'Dura[çc][ãa]o[:\s]+(\d+)\s*(?:horas?|h)',
            
            # Horas simples
            r'(\d+)\s*(?:horas?|h)(?:\s+aula|\s+de\s+(?:dura[çc][ãa]o|carga))?',
            
            # Horas e minutos
            r'(\d+)\s*(?:horas?|h)\s*(?:e\s*)?(\d+)?\s*(?:minutos?|min)?',
        ]
        
        for padrao in padroes_duracao:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                horas = match.group(1)
                # Valida que é um número razoável (1-999 horas)
                if horas.isdigit() and 1 <= int(horas) <= 999:
                    minutos = match.group(2) if len(match.groups()) > 1 else None
                    if minutos and minutos.isdigit():
                        info['duracao'] = f"{horas}h{minutos}min"
                    else:
                        info['duracao'] = f"{horas}h"
                    break
        
        # ===== EXTRAÇÃO DE DATA =====
        padroes_data = [
            # Formato brasileiro: "27 de Maio de 2025"
            r'(\d{1,2}\s+de\s+(?:janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+\d{4})',
            
            # Com "Data:"
            r'Data[:\s]+(\d{1,2}\s+de\s+[A-Za-zçãõáéíóúâêôà]+\s+de\s+\d{4})',
            r'Data[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
            
            # Formatos numéricos: DD/MM/YYYY ou DD-MM-YYYY
            r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})\b',
            
            # Formato ISO: YYYY-MM-DD
            r'\b(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b',
            
            # "em DD de MÊS de YYYY"
            r'em\s+(\d{1,2}\s+de\s+[A-Za-zçãõáéíóúâêôà]+\s+de\s+\d{4})',
        ]
        
        for padrao in padroes_data:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                data = match.group(1).strip()
                # Valida que tem pelo menos um dígito (ano)
                if re.search(r'\d{4}', data):
                    info['data'] = data
                    break
        
        return info
    
    def obter_ano(self, data_str):
        """Extrai ano da data"""
        if not data_str:
            return datetime.now().year
        
        # Busca por 4 dígitos seguidos (ano)
        match = re.search(r'\d{4}', data_str)
        if match:
            return match.group(0)
        
        # Busca por 2 dígitos no final (ano abreviado)
        match = re.search(r'\d{2}$', data_str)
        if match:
            ano = int(match.group(0))
            return f"20{ano}" if ano < 50 else f"19{ano}"
        
        return datetime.now().year
    
    def limpar_nome_arquivo(self, texto):
        """Remove caracteres inválidos para nome de arquivo"""
        if not texto:
            return "Desconhecido"
        # Remove caracteres especiais
        texto = re.sub(r'[<>:"/\\|?*]', '', texto)
        # Limita tamanho
        return texto[:100].strip()
    
    def renomear_certificado(self, caminho_original, info):
        """Renomeia o certificado baseado nas informações extraídas"""
        if not all([info.get('nome'), info.get('curso')]):
            print(f"  ⚠ Informações incompletas para renomear")
            return None
        
        nome = self.limpar_nome_arquivo(info['nome'])
        curso = self.limpar_nome_arquivo(info['curso'])
        ano = self.obter_ano(info.get('data'))
        
        # Cria novo nome
        novo_nome = f"{nome} - {curso} - {ano}.pdf"
        
        # Caminho completo
        pasta = os.path.dirname(caminho_original)
        novo_caminho = os.path.join(pasta, novo_nome)
        
        # Renomeia (evita sobrescrever)
        contador = 1
        while os.path.exists(novo_caminho):
            novo_nome = f"{nome} - {curso} - {ano} ({contador}).pdf"
            novo_caminho = os.path.join(pasta, novo_nome)
            contador += 1
        
        try:
            os.rename(caminho_original, novo_caminho)
            print(f"  ✓ Renomeado: {novo_nome}")
            return novo_caminho
        except Exception as e:
            print(f"  ❌ Erro ao renomear: {e}")
            return None
    
    def gerar_relatorio_csv(self, pasta_destino):
        """Gera relatório CSV com informações dos certificados"""
        if not self.certificados_processados:
            return
        
        arquivo_csv = os.path.join(pasta_destino, f"relatorio_certificados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        try:
            with open(arquivo_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
                campos = ['Nome', 'Curso', 'Duração', 'Data', 'Arquivo']
                writer = csv.DictWriter(csvfile, fieldnames=campos)
                
                writer.writeheader()
                for cert in self.certificados_processados:
                    writer.writerow({
                        'Nome': cert.get('nome', ''),
                        'Curso': cert.get('curso', ''),
                        'Duração': cert.get('duracao', ''),
                        'Data': cert.get('data', ''),
                        'Arquivo': cert.get('arquivo', '')
                    })
            
            print(f"\n📊 Relatório gerado: {arquivo_csv}")
            return arquivo_csv
        except Exception as e:
            print(f"❌ Erro ao gerar relatório: {e}")
            return None
    
    def processar_certificados(self):
        """Processa todos os certificados na pasta selecionada"""
        pasta = self.selecionar_pasta()
        
        if not pasta:
            print("❌ Nenhuma pasta selecionada.")
            return
        
        # Garante que dados de português estão instalados
        print("\n🔍 Verificando dados de OCR...")
        self.garantir_dados_portugues()
        
        print(f"\n📁 Processando certificados em: {pasta}\n")
        
        # Busca arquivos PDF
        arquivos_pdf = [f for f in os.listdir(pasta) if f.lower().endswith('.pdf')]
        
        if not arquivos_pdf:
            print("❌ Nenhum arquivo PDF encontrado na pasta.")
            return
        
        print(f"📄 Encontrados {len(arquivos_pdf)} arquivos PDF\n")
        print("=" * 70)
        
        for idx, arquivo in enumerate(arquivos_pdf, 1):
            caminho_completo = os.path.join(pasta, arquivo)
            print(f"\n[{idx}/{len(arquivos_pdf)}] {arquivo}")
            
            # Extrai texto
            texto = self.extrair_texto_pdf(caminho_completo)
            
            if not texto:
                print(f"  ⚠ Não foi possível extrair texto")
                continue
            
            # Extrai informações
            info = self.extrair_informacoes(texto)
            
            if not info or not info.get('nome'):
                print(f"  ⚠ Não foi possível extrair informações")
                continue
            
            print(f"  ✓ Nome: {info.get('nome')}")
            print(f"  ✓ Curso: {info.get('curso')}")
            print(f"  ✓ Duração: {info.get('duracao')}")
            print(f"  ✓ Data: {info.get('data')}")
            
            # Renomeia arquivo
            novo_caminho = self.renomear_certificado(caminho_completo, info)
            
            if novo_caminho:
                info['arquivo'] = os.path.basename(novo_caminho)
                self.certificados_processados.append(info)
        
        print("\n" + "=" * 70)
        
        # Gera relatório
        if self.certificados_processados:
            self.gerar_relatorio_csv(pasta)
            print(f"\n✅ Processados {len(self.certificados_processados)} de {len(arquivos_pdf)} certificados!")
        else:
            print("\n⚠ Nenhum certificado foi processado com sucesso.")


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main():
    print("=" * 70)
    print("         GERENCIADOR DE CERTIFICADOS - Versão Completa")
    print("=" * 70)
    print("\n🔍 Iniciando verificação do sistema...")
    
    # Verifica e instala dependências
    if not verificar_e_instalar_dependencias():
        print("\n❌ Não foi possível configurar todas as dependências")
        print("   O programa pode não funcionar corretamente")
        print()
        resposta = input("Deseja continuar mesmo assim? (S/N): ")
        if resposta.lower() not in ['s', 'sim', 'y', 'yes']:
            return
    
    print("\n" + "=" * 70)
    print("         PROCESSAMENTO DE CERTIFICADOS")
    print("=" * 70)
    print("\n📋 Este programa irá:")
    print("  1. Ler certificados PDF (com OCR se necessário)")
    print("  2. Extrair: Nome, Curso, Duração e Data")
    print("  3. Renomear: Nome - Curso - Ano.pdf")
    print("  4. Gerar relatório CSV com todas as informações")
    print()
    
    input("Pressione ENTER para selecionar a pasta com os certificados...")
    
    # Executa processamento
    gerenciador = GerenciadorCertificados()
    gerenciador.processar_certificados()
    
    print("\n" + "=" * 70)
    print("         PROCESSO CONCLUÍDO!")
    print("=" * 70)
    input("\nPressione ENTER para sair...")


if __name__ == "__main__":
    main()
