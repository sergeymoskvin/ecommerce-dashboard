import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

# ============================================
# 1. НАСТРОЙКА СТРАНИЦЫ
# ============================================
st.set_page_config(page_title="Анализ интернет-магазина", layout="wide")
st.title("📊 Дашборд анализа эффективности интернет-магазина")
st.markdown("Загрузите данные или используйте файлы из папки `data/`.")

# ============================================
# 2. ЗАГРУЗКА ДАННЫХ
# ============================================
@st.cache_data
def load_data(file_path=None, uploaded_file=None):
    """Загружает CSV-файл в DataFrame."""
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)
    elif file_path and os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        return None

# Попытка загрузки из локальной папки data/
items = load_data(file_path="data/items.csv")
orders = load_data(file_path="data/orders.csv")
users = load_data(file_path="data/users.csv")

# Если файлы не найдены, используем загрузчик вручную
if items is None or orders is None or users is None:
    st.warning("Локальные файлы не найдены. Загрузите все три CSV-файла вручную.")
    col1, col2, col3 = st.columns(3)
    with col1:
        items_file = st.file_uploader("Товары (items.csv)", type="csv")
    with col2:
        orders_file = st.file_uploader("Заказы (orders.csv)", type="csv")
    with col3:
        users_file = st.file_uploader("Пользователи (users.csv)", type="csv")

    if items_file and orders_file and users_file:
        items = load_data(uploaded_file=items_file)
        orders = load_data(uploaded_file=orders_file)
        users = load_data(uploaded_file=users_file)

# Если данные не загружены, останавливаем приложение
if items is None or orders is None or users is None:
    st.error("Не удалось загрузить данные. Проверьте наличие файлов.")
    st.stop()

# ============================================
# 3. ОЧИСТКА И ПРЕОБРАЗОВАНИЕ ДАННЫХ
# ============================================
st.header("🧹 Очистка данных")

# Приведение типов
orders['order_date'] = pd.to_datetime(orders['order_date'], errors='coerce')
users['registration_date'] = pd.to_datetime(users['registration_date'], errors='coerce')
orders['quantity'] = pd.to_numeric(orders['quantity'], errors='coerce')
orders['price_per_unit'] = pd.to_numeric(orders['price_per_unit'], errors='coerce')
items['base_price'] = pd.to_numeric(items['base_price'], errors='coerce')

# Удаление строк с критическими пропусками
orders.dropna(subset=['order_id', 'user_id', 'item_id', 'quantity', 'order_date', 'price_per_unit'], inplace=True)
items.dropna(subset=['item_id', 'item_name', 'category'], inplace=True)
users.dropna(subset=['user_id'], inplace=True)

# Заполнение пропусков в категориях (если есть)
items['category'] = items['category'].fillna('Unknown')

# Удаление дубликатов
orders.drop_duplicates(subset=['order_id'], inplace=True)
items.drop_duplicates(subset=['item_id'], inplace=True)
users.drop_duplicates(subset=['user_id'], inplace=True)

st.success(f"Очистка завершена. Заказов: {len(orders)}, товаров: {len(items)}, пользователей: {len(users)}")

# ============================================
# 4. ОБЪЕДИНЕНИЕ ТАБЛИЦ
# ============================================
st.header("🔗 Объединение таблиц")

# Объединяем orders с users (по user_id)
df = orders.merge(users, on='user_id', how='left')
# Объединяем с items (по item_id)
df = df.merge(items, on='item_id', how='left')

# Добавляем выручку по каждой позиции (quantity * price_per_unit)
df['revenue'] = df['quantity'] * df['price_per_unit']

# Добавляем день недели заказа
df['weekday'] = df['order_date'].dt.day_name()

st.write(f"Итоговый объединённый DataFrame: **{df.shape[0]} строк, {df.shape[1]} столбцов**")

# ============================================
# 5. БЛОК «СЫРЫЕ ДАННЫЕ»
# ============================================
st.header("📄 Сырые данные")

# Фильтры для интерактивности
col1, col2 = st.columns(2)
with col1:
    min_date = df['order_date'].min().date()
    max_date = df['order_date'].max().date()
    date_range = st.date_input(
        "Фильтр по дате заказа",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
with col2:
    categories = ['Все'] + list(df['category'].unique())
    selected_category = st.selectbox("Фильтр по категории", categories)

# Применяем фильтры
filtered_df = df.copy()
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df['order_date'].dt.date >= start_date) &
        (filtered_df['order_date'].dt.date <= end_date)
    ]
elif isinstance(date_range, list) and len(date_range) == 1:
    filtered_df = filtered_df[filtered_df['order_date'].dt.date == date_range[0]]

if selected_category != 'Все':
    filtered_df = filtered_df[filtered_df['category'] == selected_category]

# Отображение таблицы
st.dataframe(filtered_df)

# ============================================
# 6. БЛОК «КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ»
# ============================================
st.header("🔑 Ключевые показатели")

# Расчёт метрик
total_orders = filtered_df['order_id'].nunique()        # общее количество заказов
total_revenue = filtered_df['revenue'].sum()            # общая выручка
unique_users = filtered_df['user_id'].nunique()         # уникальные пользователи
average_check = total_revenue / total_orders if total_orders > 0 else 0  # средний чек

col1, col2, col3, col4 = st.columns(4)
col1.metric("Общее количество заказов", f"{total_orders:,}")
col2.metric("Общая выручка", f"{total_revenue:,.2f} ₽")
col3.metric("Уникальные пользователи", f"{unique_users:,}")
col4.metric("Средний чек", f"{average_check:,.2f} ₽")

# ============================================
# 7. БЛОК «ВИЗУАЛИЗАЦИЯ»
# ============================================
st.header("📈 Визуализация")

# --- 7.1 Топ-10 товаров по выручке ---
st.subheader("Топ-10 товаров по выручке")
top_products = (
    filtered_df.groupby('item_name')['revenue']
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

fig1, ax1 = plt.subplots(figsize=(10, 5))
top_products.sort_values().plot(kind='barh', ax=ax1, color='steelblue')
ax1.set_xlabel('Выручка, ₽')
ax1.set_title('Топ-10 товаров по выручке')
st.pyplot(fig1)

# --- 7.2 Выручка по категориям ---
st.subheader("Выручка по категориям")
category_revenue = filtered_df.groupby('category')['revenue'].sum()

fig2, ax2 = plt.subplots(figsize=(8, 8))
ax2.pie(
    category_revenue,
    labels=category_revenue.index,
    autopct='%1.1f%%',
    startangle=90,
    colors=plt.cm.Paired.colors
)
ax2.set_title('Доля выручки по категориям')
st.pyplot(fig2)

# --- 7.3 Заказы по дням недели ---
st.subheader("Заказы по дням недели")
orders_by_weekday = filtered_df.groupby('weekday')['order_id'].nunique()

# Упорядочиваем дни недели
weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
orders_by_weekday = orders_by_weekday.reindex(weekday_order, fill_value=0)

fig3, ax3 = plt.subplots(figsize=(10, 5))
orders_by_weekday.plot(kind='line', marker='o', ax=ax3, color='coral')
ax3.set_xlabel('День недели')
ax3.set_ylabel('Количество заказов')
ax3.set_title('Количество заказов по дням недели')
ax3.grid(True)
st.pyplot(fig3)

# ============================================
# 8. БЛОК «АНАЛИТИЧЕСКИЕ ВЫВОДЫ»
# ============================================
st.header("💡 Аналитические выводы")

# Автоматически формируем выводы на основе данных
if not top_products.empty:
    top_product_name = top_products.index[0]
    top_product_revenue = top_products.iloc[0]
else:
    top_product_name = "Н/Д"
    top_product_revenue = 0

if not category_revenue.empty:
    top_category = category_revenue.idxmax()
    top_category_share = (category_revenue.max() / category_revenue.sum()) * 100
else:
    top_category = "Н/Д"
    top_category_share = 0

if not orders_by_weekday.empty:
    busiest_day = orders_by_weekday.idxmax()
    busiest_day_orders = orders_by_weekday.max()
else:
    busiest_day = "Н/Д"
    busiest_day_orders = 0

st.markdown(f"""
1. **Товар-лидер продаж** — **{top_product_name}**. Этот товар принёс выручку **{top_product_revenue:,.2f} ₽**, что делает его самым прибыльным в выбранном периоде.  
2. **Основная категория** — **{top_category}**. На неё приходится **{top_category_share:.1f}%** всей выручки.  
3. **Пик заказов** наблюдается в **{busiest_day}** (количество заказов: {busiest_day_orders}). Это может указывать на повышенный спрос в этот день недели или успешные маркетинговые акции.  
""")

st.markdown("---")
st.caption("Дашборд создан в рамках итогового проекта.")