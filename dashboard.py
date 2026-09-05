import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
from datetime import datetime
import csv

def update_data():
    global df
    try:
        df = pd.read_csv('orders.csv')
        # Преобразование дат для корректной работы графиков
        df['Deadline'] = pd.to_datetime(df['Deadline'])
        df['OrderID'] = df['OrderID'].astype(str)
        
        # Отладочная информация
        print("Данные загружены:")
        print(f"Колонки: {df.columns.tolist()}")
        print(f"Уникальные менеджеры: {df['Manager'].unique()}")
        print(f"Всего записей: {len(df)}")
        
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
        # Создаем пустой DataFrame с правильной структурой
        df = pd.DataFrame(columns=['OrderID', 'Client', 'Service', 'Deadline', 'Budget', 'Status', 'Manager'])

# Создание экземпляра приложения
app = dash.Dash(__name__)

# Загрузка данных
update_data()

# Определение структуры дашборда
app.layout = html.Div([
    html.Div([
        html.H1('Дашборд анализа данных о заказах консалтинговой компании', 
                style={'textAlign': 'center', 'color': '#2c3e50'}),
        html.P('Этот дашборд предоставляет аналитику по управлению заказами в реальном времени.',
               style={'textAlign': 'center', 'color': '#7f8c8d'}),
        html.Div([
            html.Label('Выберите менеджера:', style={'fontSize': 18, 'marginRight': '10px'}),
            dcc.Dropdown(
                id='manager-dropdown',
                options=[],  # Начально пустой список
                value='all',
                clearable=False,
                style={'width': '50%', 'margin': '0 auto'}
            ),
        ], style={'textAlign': 'center', 'marginBottom': '30px'}),
        
        html.Div(id='debug-info', style={'color': 'red', 'textAlign': 'center', 'marginBottom': '10px'}),
        
        dcc.Interval(
            id='interval-component',
            interval=60*1000,  # Обновление каждую минуту
            n_intervals=0
        )
    ], style={'marginBottom': '30px', 'padding': '20px', 'backgroundColor': '#ecf0f1'}),

    # Первая строка графиков
    html.Div([
        html.Div([
            dcc.Graph(id='budget-timeline'),
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            dcc.Graph(id='status-histogram'),
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),
    ]),

    # Вторая строка графиков
    html.Div([
        html.Div([
            dcc.Graph(id='service-pie-chart'),
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            dcc.Graph(id='budget-box-plot'),
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),
    ]),

    # Третья строка графиков
    html.Div([
        html.Div([
            dcc.Graph(id='deadline-scatter'),
        ], style={'width': '96%', 'display': 'inline-block', 'padding': '10px'}),
    ]),

], style={'padding': '20px', 'fontFamily': 'Arial, sans-serif'})

# Callback для обновления списка менеджеров
@app.callback(
    [Output('manager-dropdown', 'options'),
     Output('debug-info', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_manager_options(n):
    update_data()
    
    try:
        if not df.empty and 'Manager' in df.columns:
            managers = df['Manager'].unique()
            # Убираем пустые значения
            managers = [m for m in managers if pd.notna(m) and str(m).strip() != '']
            options = [{'label': 'Все менеджеры', 'value': 'all'}] + [{'label': str(m), 'value': str(m)} for m in managers]
            
            debug_text = f"Доступно менеджеров: {len(managers)} | Всего заказов: {len(df)}"
            print(f"Обновлен список менеджеров: {[m['label'] for m in options]}")
            
            return options, debug_text
        else:
            debug_text = "Нет данных о менеджерах в CSV файле"
            return [{'label': 'Все менеджеры', 'value': 'all'}], debug_text
            
    except Exception as e:
        debug_text = f"Ошибка при загрузке менеджеров: {str(e)}"
        return [{'label': 'Все менеджеры', 'value': 'all'}], debug_text

# Callback для обновления графиков
@app.callback(
    [Output('budget-timeline', 'figure'),
     Output('status-histogram', 'figure'),
     Output('service-pie-chart', 'figure'),
     Output('budget-box-plot', 'figure'),
     Output('deadline-scatter', 'figure')],
    [Input('manager-dropdown', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_charts(selected_manager, n):
    # Обновление данных
    update_data()
    
    # Проверка на пустые данные
    if df.empty:
        empty_fig = px.scatter(title="Нет данных для отображения")
        empty_fig.update_layout(plot_bgcolor='white', height=400)
        return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig
    
    # Фильтрация данных по менеджеру
    if selected_manager != 'all':
        filtered_df = df[df['Manager'] == selected_manager]
        title_suffix = f" (Менеджер: {selected_manager})"
    else:
        filtered_df = df
        title_suffix = " (Все менеджеры)"

    # Проверка на пустой отфильтрованный DataFrame
    if filtered_df.empty:
        empty_fig = px.scatter(title=f"Нет данных для менеджера: {selected_manager}")
        empty_fig.update_layout(plot_bgcolor='white', height=400)
        return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig

    # 1. Линейный график "Динамика бюджета заказов по времени"
    try:
        timeline_df = filtered_df.copy()
        timeline_df = timeline_df.sort_values('Deadline')
        budget_timeline = px.line(
            timeline_df, 
            x='Deadline', 
            y='Budget',
            color='Status',
            title=f'Динамика бюджета заказов по времени{title_suffix}',
            markers=True
        )
        budget_timeline.update_layout(
            xaxis_title='Срок исполнения',
            yaxis_title='Бюджет (руб.)',
            plot_bgcolor='rgba(240, 240, 240, 0.8)',
            height=400
        )
    except Exception as e:
        budget_timeline = px.scatter(title=f"Ошибка в линейном графике: {str(e)}")
        budget_timeline.update_layout(height=400)

    # 2. Гистограмма "Количество заказов по статусам"
    try:
        status_histogram = px.histogram(
            filtered_df, 
            x='Status',
            title=f'Распределение заказов по статусам{title_suffix}',
            color='Status',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        status_histogram.update_layout(
            xaxis_title='Статус заказа',
            yaxis_title='Количество заказов',
            plot_bgcolor='rgba(240, 240, 240, 0.8)',
            height=400
        )
    except Exception as e:
        status_histogram = px.scatter(title=f"Ошибка в гистограмме: {str(e)}")
        status_histogram.update_layout(height=400)

    # 3. Круговая диаграмма "Распределение заказов по типам услуг"
    try:
        service_pie = px.pie(
            filtered_df, 
            names='Service', 
            values='Budget',
            title=f'Распределение бюджета по типам услуг{title_suffix}'
        )
        service_pie.update_traces(textposition='inside', textinfo='percent+label')
        service_pie.update_layout(height=400)
    except Exception as e:
        service_pie = px.scatter(title=f"Ошибка в круговой диаграмме: {str(e)}")
        service_pie.update_layout(height=400)

    # 4. Боксплот "Бюджет-Статус заказа"
    try:
        budget_box = px.box(
            filtered_df, 
            x='Status', 
            y='Budget',
            title=f'Распределение бюджета по статусам заказов{title_suffix}',
            color='Status'
        )
        budget_box.update_layout(
            xaxis_title='Статус заказа',
            yaxis_title='Бюджет (руб.)',
            plot_bgcolor='rgba(240, 240, 240, 0.8)',
            height=400
        )
    except Exception as e:
        budget_box = px.scatter(title=f"Ошибка в боксплоте: {str(e)}")
        budget_box.update_layout(height=400)

    # 5. Точечный график "Срок исполнения-Бюджет заказа"
    try:
        deadline_scatter = px.scatter(
            filtered_df, 
            x='Deadline', 
            y='Budget',
            color='Service',
            size='Budget',
            title=f'Зависимость бюджета от срока исполнения{title_suffix}',
            hover_data=['Client', 'Manager']
        )
        deadline_scatter.update_layout(
            xaxis_title='Срок исполнения',
            yaxis_title='Бюджет (руб.)',
            plot_bgcolor='rgba(240, 240, 240, 0.8)',
            height=400
        )
    except Exception as e:
        deadline_scatter = px.scatter(title=f"Ошибка в точечном графике: {str(e)}")
        deadline_scatter.update_layout(height=400)

    return budget_timeline, status_histogram, service_pie, budget_box, deadline_scatter

# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8050)