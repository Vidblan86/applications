# Instalar dependencias (solo la primera vez)
# pip install gspread oauth2client gspread-dataframe requests beautifulsoup4 pandas

# 1. Montar Google Drive
# from google.colab import drive
# drive.mount('/content/drive')

# 2. Imports y autenticación
import json, pandas as pd, requests, string
from bs4 import BeautifulSoup
from datetime import datetime
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# Leer credenciales desde Drive
with open('/content/drive/MyDrive/00_Job_Search_UK/credentials.json') as f:
    creds_dict = json.load(f)
gc = gspread.service_account_from_dict(creds_dict)

# 3. Abrir Google Sheet
SHEET_ID = '1vsfOz8lPxG58n6kl9fnzCX0y_wmcirhVhHOZWbzeBGw'
sh = gc.open_by_key(SHEET_ID)
ws = sh.sheet1

# 4. Cargar datos en DataFrame
df = get_as_dataframe(ws, evaluate_formulas=True, skip_blank_rows=False)

# 5. Asegurar columna 'state' y marcar nuevas filas
if 'state' not in df.columns:
    df['state'] = 0                # inicializamos todo a 0
else:
    df['state'] = df['state'].fillna(0).astype(int)

# Máscara de filas sin descripción, company y title
mask = (
    df['link'].notna() &
    df['description'].isna() &
    df['company'].isna() &
    df['title'].isna()
)
df.loc[mask, 'state'] = 1         # marcamos con 1 las nuevas filas a procesar

# 6. Procesar filas nuevas (state == 1)
rows_to_process = df[mask]
today = datetime.now().strftime('%Y-%m-%d')
for idx, row in rows_to_process.iterrows():
    url = row['link']
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Extraer campos
        title = soup.title.string.strip() if soup.title and soup.title.string else ''
        desc_tag = soup.find('meta', attrs={'name':'description'})
        description = desc_tag['content'].strip() if desc_tag and desc_tag.get('content') else ''
        comp_tag = soup.find('meta', attrs={'property':'og:site_name'})
        company = comp_tag['content'].strip() if comp_tag and comp_tag.get('content') else ''
        # Asignar al DataFrame
        df.at[idx, 'title'] = title
        df.at[idx, 'description'] = description
        df.at[idx, 'company'] = company
        df.at[idx, 'last_modified'] = today
    except Exception as e:
        print(f"Error fila {idx} ({url}): {e}")

# 7. Sobrescribir la Sheet con datos actualizados
ws.clear()
set_with_dataframe(ws, df)

# 8. Aplicar tachado a filas descartadas (state != 1)
ncols = df.shape[1]
end_col = list(string.ascii_uppercase)[ncols - 1]
for idx in df[df['state'] != 1].index:
    row_num = idx + 2  # +2 porque la fila 1 son encabezados
    cell_range = f"A{row_num}:{end_col}{row_num}"
    ws.format(cell_range, {"textFormat": {"strikethrough": True}})

print("Script completado: datos extraídos, Sheet actualizada y filas descartadas tachadas.")
