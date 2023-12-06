from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse
import os
import imaplib
import email
from datetime import datetime
import glob
import re
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from email.header import decode_header
import json
from typing import List

app = FastAPI()


@app.get("/")
async def root():
  return {"message": "TCC DO VITOR"}


@app.get("/extrair_pdf")
def extrair_pdf(emailUsuario: str, password: str, start_date: str,
                end_date: str):
  # Conectar-se ao servidor IMAP
  mail = imaplib.IMAP4_SSL('imap.gmail.com')

  # Fazer login
  mail.login(emailUsuario, password)

  # Selecionar a caixa de entrada
  mail.select('inbox')

  # Converter as datas para o formato correto
  start_date = datetime.strptime(start_date, "%d/%m/%Y").strftime("%d-%b-%Y")
  end_date = datetime.strptime(end_date, "%d/%m/%Y").strftime("%d-%b-%Y")

  # Excluir todos os arquivos no diretório 'arquivos'
  files = glob.glob('./arquivos/*')
  for f in files:
    os.remove(f)

  # Pesquisar por e-mails com anexos em PDF
  result, data = mail.search(None, f'SINCE "{start_date}" BEFORE "{end_date}"',
                             '(BODY "pdf")',
                             'OR SUBJECT "fatura" SUBJECT "boleto"')
  #result, data = mail.search(None, 'SINCE "01-Jan-2023" BEFORE "01-Feb-2023"', '(BODY "pdf")', 'OR SUBJECT "fatura" SUBJECT "boleto"')

  # Percorrer os e-mails encontrados
  for num in data[0].split():
    # Baixar o e-mail e convertê-lo em um objeto email
    typ, msg_data = mail.fetch(num, '(RFC822)')
    print(type(msg_data[0][1]), msg_data[0][1])
    msg = email.message_from_bytes(msg_data[0][1])

    # Verificar se o e-mail possui anexos
    has_attachments = any(part.get_content_maintype() == 'application'
                          and part.get_content_subtype() == 'pdf'
                          for part in msg.walk())

    sender = msg['From']
    match = re.search(r'@(.+?)\.', sender)
    sender_name = match.group(1) if match else sender

    date_str = msg['Date']
    formatted_date = parsedate_to_datetime(date_str).strftime(
        '%d-%m-%Y_') if date_str else 'DataDesconhecida'

    if has_attachments:
      # Criar um dicionário para armazenar informações do e-mail
      email_data = {
          'Data_email': formatted_date,
          'Remetente': sender_name,
          'Destinatario': msg["To"],
          'Assunto': msg["Subject"],
          'Corpo': '',
      }

      # Percorrer as partes do e-mail
      for part in msg.walk():
        if part.get_content_type() == 'text/plain':
          email_data['Corpo'] += part.get_payload(decode=True).decode("utf-8")
        elif part.get_content_type() == 'text/html':
          # Use BeautifulSoup para extrair o texto do HTML
          soup = BeautifulSoup(
              part.get_payload(decode=True).decode("utf-8"), "html.parser")
          email_data['Corpo'] += soup.get_text()

      email_data['Corpo'] = re.sub(r'\s+', ' ', email_data['Corpo']).strip()

      # Salvar o dicionário como JSON
      output_filename = f'./arquivos/{formatted_date + sender_name}.json'
      with open(output_filename, 'w', encoding='utf-8') as output_file:
        json.dump(email_data, output_file, ensure_ascii=False, indent=2)

      # Percorrer os anexos do e-mail e salvá-los
      for part in msg.walk():
        if part.get_content_maintype(
        ) == 'application' and part.get_content_subtype() == 'pdf':
          # Extraindo o nome do arquivo PDF do anexo
          filename = formatted_date + sender_name

          # Substitua isso pelo diretório onde você quer armazenar os PDFs
          pdf_directory = './arquivos'

          # Salvar o anexo PDF
          pdf_filename = os.path.join(pdf_directory, filename) + '.pdf'
          try:
            with open(pdf_filename, 'wb') as f:
              f.write(part.get_payload(decode=True))
          except Exception as e:
            print(f"Erro ao salvar anexo PDF: {e}")
            continue  # Continue para o próximo anexo em caso de erro


'''
@app.get("/listar_pdfs")
def listar_pdfs():
  pdf_directory = './arquivos'

  pdfs = []
  for filename in os.listdir(pdf_directory):
    filepath = os.path.join(pdf_directory, filename)
    size = os.path.getsize(filepath)
    creation_time = datetime.utcfromtimestamp(os.path.getctime(filepath))
    pdfs.append({"name": filename, "size": size, "data": creation_time})

  return pds'''
''' #certo
@app.get("/listar_pdfs")
def listar_pdfs():
  pdf_directory = './arquivos'

  pdfs = []
  jsons = []

  for filename in os.listdir(pdf_directory):
    filepath = os.path.join(pdf_directory, filename)
    size = os.path.getsize(filepath)
    creation_time = datetime.utcfromtimestamp(os.path.getctime(filepath))

    if filename.lower().endswith('.pdf'):
      pdfs.append({"name": filename, "size": size, "data": creation_time})
    elif filename.lower().endswith('.json'):
      try:
        with open(filepath, 'r', encoding='utf-8') as json_file:
          json_content = json.load(json_file)
        jsons.append({
            "name": filename,
            "size": size,
            "data": creation_time,
            "content": json_content
        })
      except json.JSONDecodeError as e:
        jsons.append({
            "name": filename,
            "size": size,
            "data": creation_time,
            "error": f"Erro ao decodificar JSON: {e}"
        })
  #return {"pdfs": pdfs, "jsons": jsons}
  return pdfs
'''


@app.get("/listar_pdfs")
def listar_pdfs():
  pdf_directory = './arquivos'

  entries = []

  for filename in os.listdir(pdf_directory):
    filepath = os.path.join(pdf_directory, filename)
    size = os.path.getsize(filepath)
    creation_time = datetime.utcfromtimestamp(os.path.getctime(filepath))

    if filename.lower().endswith('.pdf'):
      entry = {
          "name": filename,
          "size": size,
          "data": creation_time,
          "Data_email": None,
          "Remetente": None,
          "Destinatario": None,
          "Assunto": None,
          "Corpo": None
      }

      # Tente encontrar o arquivo JSON correspondente
      json_filename = filename.replace('.pdf', '.json')
      json_filepath = os.path.join(pdf_directory, json_filename)

      if os.path.exists(json_filepath):
        try:
          with open(json_filepath, 'r', encoding='utf-8') as json_file:
            json_content = json.load(json_file)

          # Adicione as informações do JSON diretamente na entrada
          entry.update(json_content)
        except json.JSONDecodeError as e:
          entry["error"] = f"Erro ao decodificar JSON: {e}"

      entries.append(entry)

  return {"dadosPDF": entries}


'''
@app.get("/listar_pdfs")
def listar_pdfs():
    pdf_directory = './arquivos'

    pdfs = []
    jsons = []

    for filename in os.listdir(pdf_directory):
        filepath = os.path.join(pdf_directory, filename)
        size = os.path.getsize(filepath)
        creation_time = datetime.utcfromtimestamp(os.path.getctime(filepath))

        if filename.lower().endswith('.pdf'):
            pdfs.append({"name": filename, "size": size, "data": creation_time})
        elif filename.lower().endswith('.json'):
            try:
                with open(filepath, 'r', encoding='utf-8') as json_file:
                    json_content = json.load(json_file)

                # Adicione aqui a lógica para extrair as partes específicas do corpo do e-mail
                corpo = json_content.get("Corpo", "")  # Supondo que o campo no JSON seja "Corpo"

                # Exemplo: Extrair informações usando expressões regulares
                remetente_match = re.search(r'Remetente: (.+)', corpo)
                remetente = remetente_match.group(1) if remetente_match else None

                destinatario_match = re.search(r'Destinatario: (.+)', corpo)
                destinatario = destinatario_match.group(1) if destinatario_match else None

                assunto_match = re.search(r'Assunto: (.+)', corpo)
                assunto = assunto_match.group(1) if assunto_match else None

                # Adicione as partes extraídas ao JSON
                jsons.append({
                    "name": filename,
                    "size": size,
                    "data": creation_time,
                    "Remetente": remetente,
                    "Destinatario": destinatario,
                    "Assunto": assunto,
                })

            except json.JSONDecodeError as e:
                jsons.append({"name": filename, "size": size, "data": creation_time, "error": f"Erro ao decodificar JSON: {e}"})

    return {"pdfs": pdfs, "jsons": jsons}'''


@app.get("/obter_pdf/{pdf_name}")
def obter_pdf(pdf_name: str):
  # Substitua isso pelo diretório onde você está armazenando os PDFs
  pdf_directory = './arquivos'
  return FileResponse(path=os.path.join(pdf_directory, pdf_name),
                      filename=pdf_name,
                      media_type="application/pdf")
