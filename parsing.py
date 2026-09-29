import pandas as pd
import requests
import matplotlib.pyplot as plt
import logging


def data_preparation():

    df = pd.read_excel('Database.xlsx', header=2)
    df = df.dropna(how='all')
    df.columns = df.columns.str.strip()
    df = df[df['Тип субъекта'] == 'Юридическое лицо']
    df = df[df['Категория'].isin(['Малое предприятие', 'Среднее предприятие'])]
    df = df[df['Основной вид деятельности'].str.startswith('41.20')]
    if '№ п/п' in df.columns:
        df = df.drop(columns=['№ п/п'])
    df = df.reset_index(drop=True)
    df.to_csv('cleaned_reestr.csv', index=False, encoding='utf-8-sig')

def get_inn():

    df = pd.read_csv("cleaned_reestr.csv", dtype={'ИНН':str})
    data_inn = df['ИНН']
    data_inn = data_inn[:1000]

    return data_inn

def create_session():

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

    return session

def get_org_id(session, inn):
    
    search_url = f"https://bo.nalog.gov.ru/advanced-search/organizations/search?query={inn}&page=0"
    res = session.get(search_url)
    res.raise_for_status()

    data = res.json()

    if not data.get('content'):
        raise ValueError(f"Организация не найдена по ИНН:{inn}")
    return data['content'][0]['id']

def extract_financials(session, org_id, inn):

    bfo_url = f"https://bo.nalog.gov.ru/nbo/organizations/{org_id}/bfo/"
    res = session.get(bfo_url)
    res.raise_for_status()
    bfo_data = res.json()

    if not isinstance(bfo_data, list):
        raise ValueError("Сервер вернул не список отчетов")
    
    company_data = {'ИНН': inn}
    for report in bfo_data:
        year = report.get('period')
    
        fin_res = report['typeCorrections'][0]['correction']['financialResult']
    
        value_2300 = fin_res.get('current2300', 0)
        value_2330 = fin_res.get('current2330', 0)
        value_2400 = fin_res.get('current2400', 0)
    
        company_data[f'EBIT_{year}'] = value_2330 + value_2300
        company_data[f'P_P_{year}'] = value_2400
        
    return dict(sorted(company_data.items()))

def build_dataframe(data):
    return pd.DataFrame(data)

def analys_for_growth(data, N):

    start = "P_P_2025"
    end = f"P_P_{2025 - N}"

    if start in data.columns and end in data.columns:
        data = data.dropna(subset=[start, end]).copy()
        data = data[data[end] != 0]
        growing_series = ((data[start] - data[end]) / data[end].abs()) * 100

        data[f'growing_for_{N}'] = growing_series.round().astype(int)
        return data
    
    else:
        print(f"WARNING: В таблице нет данных за {start} или {end} год!")
        return data

def build_counts_data(df_results, N):
    df_results = df_results[(df_results[f'growing_for_{N}'] <= 300) & (df_results[f'growing_for_{N}'] >= - 300)]
    
    counts_data = df_results[f'growing_for_{N}'].value_counts().reset_index()
    counts_data.columns = ['Процент роста', 'Количество компаний']
    counts_data = counts_data.sort_values(by='Процент роста')

    return counts_data

def graph_plotting(counts_data, N):

    plt.figure(figsize=(12, 6))
    plt.bar(counts_data['Процент роста'], counts_data['Количество компаний'], color='royalblue')
    plt.title(f"Распределение строительных компаний по росту прибыли (за {N} года)", fontsize=14)
    plt.xlabel("Процент роста чистой прибыли, %", fontsize=12)
    plt.ylabel("Количество компаний", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig('images/profit_growth.png', dpi=300, bbox_inches='tight')
    plt.show()

def median_ebit_graph(data):

    ebit_cols = sorted([col for col in data.columns if col.startswith('EBIT_')])
    median_result = data[ebit_cols].median()

    years = [col.split('_')[1] for col in ebit_cols]

    plt.figure(figsize=(10, 6)),
    plt.bar(years, median_result.values, color='lightblue', alpha=0.6)
    plt.plot(years, median_result.values, color='navy', marker='o', linewidth=2)
    plt.title('Динамика медианного EBIT строительных МСП по годам', fontsize=14)
    plt.xlabel('Год', fontsize=12)
    plt.ylabel('Медианный EBIT (в тыс. руб.)', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig('images/ebit_dynamics.png', dpi=300, bbox_inches='tight')
    plt.show()

def distribution_ebit_graph(data):

    ebit_cols = sorted([col for col in data.columns if col.startswith('EBIT_')])
    last_year = ebit_cols[-1].split('_')[1]

    q_low = data[ebit_cols[-1]].quantile(0.05)
    q_high = data[ebit_cols[-1]].quantile(0.95)

    data_filtred = data[(data[ebit_cols[-1]] >= q_low) & (data[ebit_cols[-1]] <= q_high)]
    median_val = data_filtred[ebit_cols[-1]].median()

    plt.figure(figsize=(12, 6))
    plt.hist(data_filtred[ebit_cols[-1]], bins=50, color='seagreen', edgecolor='black', alpha=0.8)
    plt.axvline(median_val, color='red', linestyle='dashed', linewidth=2, label=f'Медиана: {int(median_val)} тыс. руб.')
    plt.title(f'Распределение операционной прибыли (EBIT) среди компаний в {last_year} году', fontsize=14)
    plt.xlabel('EBIT (тыс. руб.)', fontsize=12)
    plt.ylabel('Количество компаний', fontsize=12)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig('images/ebit_distribution.png', dpi=300, bbox_inches='tight')
    plt.show()

