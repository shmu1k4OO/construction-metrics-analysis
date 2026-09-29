import parsing
import pandas as pd
import requests
import matplotlib.pyplot as plt
import sys
import logging


logging.basicConfig(
    filename='parser_errors.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Использование: python main.py <число лет>")
        sys.exit(1)

    try:
        N = int(sys.argv[1])
    except ValueError:
        print("Ошибка конфигурации: N должно быть целым числом")
        sys.exit(1)

    if not(1 <= N <= 4):
        print("Ошибка конфигурации: N должно быть числом от 1 до 4")
        sys.exit(1)
    
    # parsing.data_preparation()
    inn_data = parsing.get_inn()
    session = parsing.create_session()

    result = []
    total = len(inn_data)
    for count, inn in enumerate(inn_data, 1):
        try:
            org_id = parsing.get_org_id(session, inn)
            company_fin = parsing.extract_financials(session, org_id, inn)
            if company_fin:
                result.append(company_fin)
        except requests.RequestException as e:
            logging.error(f"[{count}/{total}] Сетевая ошибка для ИНН {inn}: {e}")

        except (ValueError, KeyError, TypeError, IndexError) as e:
            logging.warning(f"[{count}/{total}] Ошибка данных для ИНН {inn}: {e}")

        if count % 10 == 0:
            print(f"Обаботано: {count/total}")

    if not result:
        logging.critical("Не удалось собрать данные ни по одной компании. Работа прервана.")
        print("Не удалось собрать данные, проверьте .log-файл")
        sys.exit(1)

    logging.info(f"Сбор завершён. Успешно получены данные по {len(result)} компаниям.")

    df_results = parsing.build_dataframe(result)
    parsing.median_ebit_graph(df_results)
    parsing.distribution_ebit_graph(df_results)

    df_results = parsing.analys_for_growth(df_results, N)
    counts_data = parsing.build_counts_data(df_results, N)
    parsing.graph_plotting(counts_data, N)


    

