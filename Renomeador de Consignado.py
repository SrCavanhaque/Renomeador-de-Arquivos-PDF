import os
import re
import sys
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract

def obter_caminho_base():
    """Retorna o caminho temporário onde o PyInstaller descompacta os arquivos."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def obter_caminho_pasta_executavel():
    """Retorna o caminho real da pasta onde o arquivo .exe está salvo."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# Configuração dos caminhos dinâmicos do Tesseract e Poppler
BASE_DIR = obter_caminho_base()
TESSERACT_EXE = os.path.join(BASE_DIR, "Tesseract-OCR", "tesseract.exe")
POPPLER_BIN = os.path.join(BASE_DIR, "poppler", "bin")

# Aplica as configurações do OCR se os arquivos existirem no pacote
if os.path.exists(TESSERACT_EXE):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

def extrair_texto_ocr(caminho_pdf):
    """Converte a 1ª página do PDF em imagem e aplica OCR."""
    try:
        kwargs = {}
        if os.path.exists(POPPLER_BIN):
            kwargs['poppler_path'] = POPPLER_BIN

        imagens = convert_from_path(caminho_pdf, first_page=1, last_page=1, **kwargs)
        if imagens:
            texto = pytesseract.image_to_string(imagens[0], lang='por')
            return texto
    except Exception as e:
        print(f"[ERRO OCR] Falha ao processar {os.path.basename(caminho_pdf)}: {e}")
    return ""

def extrair_dados_primeira_pagina(caminho_pdf):
    texto_pagina1 = ""

    # 1. Tenta extrair texto direto (PDF digital)
    try:
        reader = PdfReader(caminho_pdf)
        if len(reader.pages) > 0:
            texto_pagina1 = reader.pages[0].extract_text() or ""
    except Exception:
        pass

    # 2. Se falhar ou o texto for muito curto, ativa o OCR (PDF escaneado)
    if len(texto_pagina1.strip()) < 10:
      
        texto_pagina1 = extrair_texto_ocr(caminho_pdf)

    # Regex para localizar os padrões de número
    regex_nr_doc = r"Nr.\s*Documento:\s*(\d+)"
    regex_codigo = r"Entrada:\s*(\d+)"

    match_doc = re.search(regex_nr_doc, texto_pagina1, re.IGNORECASE)
    match_cod = re.search(regex_codigo, texto_pagina1, re.IGNORECASE)

    nr_doc = match_doc.group(1) if match_doc else None
    codigo = match_cod.group(1) if match_cod else None

    return nr_doc, codigo

def renomear_pdfs_pasta_atual():
    caminho_pasta = obter_caminho_pasta_executavel()
    print("==================================================")
    print(f"Buscando arquivos na pasta:\n{caminho_pasta}")
    print("==================================================\n")

    arquivos = [f for f in os.listdir(caminho_pasta) if f.lower().endswith('.pdf')]

    if not arquivos:
        print("Nenhum arquivo PDF encontrado nesta pasta.")
        return

    print(f"Encontrados {len(arquivos)} arquivo(s) PDF.\n")

    processados = 0
    ignorados = 0

    for arquivo in arquivos:
        if arquivo.startswith("NF "):
            print(f"[IGNORADO] Já renomeado: {arquivo}")
            ignorados += 1
            continue

        caminho_antigo = os.path.join(caminho_pasta, arquivo)
        nr_doc, codigo = extrair_dados_primeira_pagina(caminho_antigo)

        if nr_doc and codigo:
            novo_nome = f"NF {nr_doc} - {codigo}.pdf"
            caminho_novo = os.path.join(caminho_pasta, novo_nome)

            contador = 1
            while os.path.exists(caminho_novo):
                novo_nome = f"NF {nr_doc} - {codigo}_v{contador}.pdf"
                caminho_novo = os.path.join(caminho_pasta, novo_nome)
                contador += 1

            os.rename(caminho_antigo, caminho_novo)
            print(f"[OK] {arquivo} ==> {novo_nome}")
            processados += 1
        else:
            print(f"[AVISO] Padrão 'Nr Doc' / 'Código' não encontrado em: {arquivo}")

    print("\n--------------------------------------------------")
    print(f"Resumo: {processados} renomeado(s) | {ignorados} ignorado(s).")

if __name__ == "__main__":
    try:
        renomear_pdfs_pasta_atual()
    except Exception as e:
        print(f"\n[ERRO CRÍTICO]: {e}")
    finally:
        print("\n--------------------------------------------------")
        input("Processo finalizado. Pressione ENTER para fechar...")