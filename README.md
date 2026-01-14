# Gerenciador de Certificados com OCR

Aplicação desktop para organização automática de certificados em PDF, utilizando OCR (Optical Character Recognition) para extrair informações e renomear arquivos de forma padronizada.

O projeto é voltado para usuários que acumulam certificados digitais (cursos, treinamentos, eventos) e precisam manter esses documentos organizados de forma eficiente e auditável.

--------------------------------------------------
## FUNCIONALIDADES
--------------------------------------------------
- Extração automática de informações a partir de certificados em PDF
- Suporte a certificados baseados em imagem (OCR) e texto nativo
- Renomeação padronizada dos arquivos:
  `Nome - Curso - Ano.pdf`
- Geração de relatório CSV com os dados extraídos
- Processamento 100% local (nenhum dado é enviado para a internet)
- Otimizado para certificados em português brasileiro

--------------------------------------------------
## TECNOLOGIAS UTILIZADAS
--------------------------------------------------
- Python 3.11+
- Tesseract OCR
- pytesseract
- pdf2image
- PyPDF2
- Pillow
- Poppler

--------------------------------------------------
## ESTRUTURA DO PROJETO
--------------------------------------------------
```
gerenciador-certificados/
|
|-- README.md
|-- LICENSE
|-- requirements.txt
|-- .gitignore
|
`-- src/
    `-- main.py
```

--------------------------------------------------
## INSTALAÇÃO
--------------------------------------------------
**Pré-requisito obrigatório:**
Tesseract OCR instalado no sistema.

**Windows:**
- Download: https://github.com/UB-Mannheim/tesseract/wiki
- Durante a instalação, habilite o idioma Portuguese
- Caminho recomendado:
  `C:\Program Files\Tesseract-OCR`

--------------------------------------------------
## EXECUTANDO VIA CÓDIGO-FONTE
--------------------------------------------------
```bash
git clone https://github.com/AlcirHagge/gerenciador-certificados.git
cd gerenciador-certificados

python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate # Linux/Mac

pip install -r requirements.txt
python src/main.py
```

--------------------------------------------------
## USO
--------------------------------------------------
1. Execute o programa
2. Selecione a pasta contendo os certificados em PDF
3. O sistema processa automaticamente:
   - Extração de texto (OCR quando necessário)
   - Identificação de nome, curso, data e duração
   - Renomeação dos arquivos
   - Geração de relatório CSV

--------------------------------------------------
## SAÍDA GERADA
--------------------------------------------------
**Arquivos renomeados no padrão:**
```
Nome - Curso - Ano.pdf
```

**Relatório CSV contendo:**
- Nome
- Curso
- Duração
- Data
- Nome final do arquivo

--------------------------------------------------
## STATUS DO PROJETO
--------------------------------------------------
Projeto em desenvolvimento, com foco em:
- Aumentar a taxa de reconhecimento
- Suporte a novos formatos de certificados
- Melhorias na interface do usuário

--------------------------------------------------
## LICENÇA
--------------------------------------------------
Este projeto está licenciado sob a licença MIT.
Consulte o arquivo LICENSE para mais detalhes.
