import json
import pandas as pd
import requests
import string
from bs4 import BeautifulSoup
from datetime import datetime
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# 1. Leer credenciales desde el archivo que crea el workflow
with open('credentials.json') as f:
    creds_dict = json.load(f)
gc = gspread.service_account_from_dict(creds_dict)

# 2. Abrir la Google Sheet
SHEET_ID = '1vsfOz8lPxG58n6kl9fnzCX0y_wmcirhVhHOZWbzeBGw'
sh = gc.open_by_key(SHEET_ID)
ws = sh.sheet1

# 3. Cargar datos en DataFrame
df = get_as_dataframe(ws, evaluate_formulas=True, skip_blank_rows=False)

# 4. Asegurar columna 'state' y marcar nuevas filas
if 'state' not in df.columns:
    df['state'] = 0
else:
    df['state'] = df['state'].fillna(0).astype(int)

mask = (
    df['link'].notna() &
    df['description'].isna() &
    df['company'].isna() &
    df['title'].isna()
)
df.loc[mask, 'state'] = 1

# 5. Procesar filas nuevas
today = datetime.now().strftime('%Y-%m-%d')
for idx, row in df[mask].iterrows():
    url = row['link']
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')

        title = soup.title.string.strip() if soup.title and soup.title.string else ''
        desc_tag = soup.find('meta', attrs={'name':'description'})
        description = desc_tag['content'].strip() if desc_tag and desc_tag.get('content') else ''
        comp_tag = soup.find('meta', attrs={'property':'og:site_name'})
        company = comp_tag['content'].strip() if comp_tag and comp_tag.get('content') else ''

        df.at[idx, 'title'] = title
        df.at[idx, 'description'] = description
        df.at[idx, 'company'] = company
        df.at[idx, 'last_modified'] = today

    except Exception as e:
        print(f"Error fila {idx} ({url}): {e}")

# 6. Sobrescribir la Sheet con datos actualizados
ws.clear()
set_with_dataframe(ws, df)

# 7. Tachado de filas descartadas (state != 1)
ncols = df.shape[1]
end_col = list(string.ascii_uppercase)[ncols - 1]
for idx in df[df['state'] != 1].index:
    row = idx + 2
    rng = f"A{row}:{end_col}{row}"
    ws.format(rng, {"textFormat": {"strikethrough": True}})

print("¡Hecho! Sheet actualizada y descartados tachados.")
