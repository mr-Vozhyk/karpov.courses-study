from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner'            : 'mr_vozhyk',
    'retries'          : 0,
    'start_date'       : datetime(2024, 9, 1),
    'schedule_interval': '00 12 * * 1'
}

dag = DAG('dag_mr_vozhyk_mini_pj',
          default_args = default_args,
          catchup = False)

def send_report_to_vk():
    import pandas as pd
    import numpy as np
    import vk_api
    import random

    today = '2019-04-02'
    
    path  = 'C:/Users/user/Karpov_courses/Аналитик_данных/AirFlow/ads_data_121288 - ads_data_121288.csv'
    ads   = pd.read_csv(path, parse_dates = [0])
    ads.drop_duplicates(inplace = True)
    print('Данные для отчета подгружены')
    
    # количество показов
    count_views = ads\
                    [ads.event == 'view']\
                    .groupby(['date','ad_id'], as_index= False)\
                    .agg({'platform':'count'})\
                    .rename(columns = {'platform':'count_view'})
    # количество кликов
    count_clicks = ads\
                    [ads.event == 'click']\
                    .groupby(['date','ad_id'], as_index= False)\
                    .agg({'platform':'count'})\
                    .rename(columns = {'platform':'count_click'})
    # CTR (click-through rate - коэффициент кликабельности) - отношение числа кликов к числу показов, в процентах
    ads_df        = count_clicks.merge(count_views)
    ads_df['ctr'] = ads_df.count_click.div(ads_df.count_view).mul(100).round(2) 

    # Cумма потраченных денег
    # формула CRM: значение из колонки ad_cost разделить на 1000 и умножить на количество показов объявления.
    ads_df['ad_cost']   = ads.ad_cost.unique()[0]
    ads_df['value_crm'] = ads_df.ad_cost.div(1000).mul(ads_df.count_view).round(2)

    print('Метрики по дням подсчитаны')
    
    # Создание Df с динамикой - мониторинг
    ads_monitoring         = ads_df[['date', 'ad_id']]
    ads_monitoring['date'] = pd.to_datetime(ads_monitoring.date)
    
    # Метрики за текущий интересующий день
    value_crm_0204 = float(ads_df[ads_df.date == today].value_crm)
    views_0204     = int(ads_df[ads_df.date == today].count_view)
    clicks_0204    = int(ads_df[ads_df.date == today].count_click)
    ctr_0204       = float(ads_df[ads_df.date == today].ctr)
    
    # Оставление в Df-мониторинге только текущего дня
    ads_monitoring = ads_monitoring[ads_monitoring.date == today]
    
    # Метрики предыдущего дня
    click_yesterday     = int(ads_df[ads_df.date == ads_df.date.values[-2]].count_click)
    view_yesterday      = int(ads_df[ads_df.date == ads_df.date.values[-2]].count_view)
    ctr_yesterday       = float(ads_df[ads_df.date == ads_df.date.values[-2]].ctr)
    value_crm_yesterday = float(ads_df[ads_df.date == ads_df.date.values[-2]].value_crm)
    
    # Добавление в Df-мониторинг данных о динамике текущего дня с предыдущим
    ads_monitoring['click_dynamic']     = clicks_0204 - click_yesterday
    ads_monitoring['view_dynamic']      = views_0204 - view_yesterday
    ads_monitoring['ctr_dynamic']       = ctr_0204 - ctr_yesterday
    ads_monitoring['value_crm_dynamic'] = value_crm_0204 - value_crm_yesterday

    # Пересчет метрик в проценты 
    value_crm_dyn_perscent = round((ads_monitoring.value_crm_dynamic.values[0].round(2)/ value_crm_yesterday)*100,2)
    views_dyn_perscent     = round((ads_monitoring.view_dynamic.values[0].round(2)/ view_yesterday)*100,2)
    clicks_dyn_perscent    = round((ads_monitoring.click_dynamic.values[0].round(2)/ click_yesterday)*100,2)
    ctr_dyn_perscent       = round((ads_monitoring.ctr_dynamic.values[0].round(2)/ ctr_yesterday)*100,2)

    # Формирование итогового человекочитаемого-отчета
    message = (f'''
        Отчет по объявлению {ads_monitoring.ad_id.values[0]} за { str(ads_monitoring.date.dt.day[1]) + ' ' + ads_monitoring.date.dt.month_name().values[0]}
        Траты:  {value_crm_0204} рублей ({ '+' if value_crm_dyn_perscent > 0 else ''}{value_crm_dyn_perscent} %)
        Показы: {views_0204} ({ '+' if views_dyn_perscent > 0 else ''}{views_dyn_perscent} %)
        Клики:  {clicks_0204} ({ '+' if clicks_dyn_perscent > 0 else ''}{clicks_dyn_perscent} %)
        CTR:    {ctr_0204} ({ '+' if ctr_dyn_perscent > 0 else ''}{ctr_dyn_perscent} %)'''
        )
    print('Отчет сформирован')
    
    # Создание файла report_{today}.txt и запись в него сообщения
    with open(f'report_{today}.txt', 'w') as file:
        file.write(message)
    print(f'Отчет сохранен под именем report_{today}.txt')

    # Отправка отчета в ВК
    app_token  = '...'
    chat_id    = 1
    my_id      = 123456789
    vk_session = vk_api.VkApi(token = app_token)
    vk         = vk_session.get_api()
    
    vk.messagessend(
        chat_id   = chat_id,
        random_id = random.randint(1,2,**31),
        message   = message
    )
    print('Отчет отправлен')