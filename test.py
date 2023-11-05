import datetime
import jpholiday
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import io
import networkx as nx
import matplotlib.pyplot as plt
import japanize_matplotlib
task_name_mapping = {
        "1": "1: 田植え準備",
        "2": "2: 耕起（田起こし",
        "3": "3: 畦塗り",
        "4": "4: 基肥",
        "5": "5: 入水",
        "6": "6: 代掻き",
        "7": "7: 種籾準備",
        "8": "8: 苗代の準備",
        "9": "9: 播種",
        "10": "10: 育苗管理",
        "11": "11: 田植え"
    }


class Calendar:
    @staticmethod
    def is_business_day(date):
        return date.weekday() < 5 and not jpholiday.is_holiday(date)

class Task:
    def __init__(self, id, man_hours_per_a, field_area=1, max_workers=1, buffer_days=0, dependencies=[]):
        self.id = id
        self.man_hours_per_a = man_hours_per_a
        self.field_area = field_area
        self.max_workers = max_workers
        self.buffer_days = buffer_days
        self.dependencies = dependencies
        self.start_date = None
        self.end_date = None

    def calculate_total_man_hours(self):
        # 作業時間を同時稼働できるトラクタや作業員の数で除算
        effective_man_hours = self.man_hours_per_a / self.max_workers
        return effective_man_hours * self.field_area

    def convert_hours_to_days(self, hours):
        return int(hours / 8) + (1 if hours % 8 > 0 else 0)


def schedule_tasks(tasks, start_date):
    task_dict = {task.id: task for task in tasks}
    scheduled_task_ids = set()
    available_tasks = [task for task in tasks if not task.dependencies]

    while available_tasks:
        task = available_tasks.pop(0)
        if task.dependencies:
            task_start = max([task_dict[dep].end_date for dep in task.dependencies]) + datetime.timedelta(days=1)
        else:
            task_start = start_date

        total_man_hours = task.calculate_total_man_hours()
        task_days_needed = task.convert_hours_to_days(total_man_hours)

        task_days_spent = 0
        current_date = task_start
        while task_days_spent < task_days_needed:
            if Calendar.is_business_day(current_date):
                task_days_spent += 1
            current_date += datetime.timedelta(days=1)

        task.start_date = task_start
#        task.end_date = current_date - datetime.timedelta(days=1)
        task.end_date = current_date - datetime.timedelta(days=1)
        task.end_date += datetime.timedelta(days=task.buffer_days)  # バッファを追加


        scheduled_task_ids.add(task.id)

        for t in task_dict.values():
            if t.id not in scheduled_task_ids and set(t.dependencies).issubset(scheduled_task_ids):
                available_tasks.append(t)

    return tasks
    
def reverse_schedule_tasks(tasks, end_date):
    tasks_by_id = {task.id: task for task in tasks}
    last_dates = {}

    for task in reversed(tasks):
        total_man_hours = task.calculate_total_man_hours()
        days_needed = task.convert_hours_to_days(total_man_hours)
        task.end_date = end_date

        while days_needed > 0:
            if Calendar.is_business_day(end_date):
                days_needed -= 1
            end_date -= datetime.timedelta(days=1)

        task.start_date = end_date - datetime.timedelta(days=task.convert_hours_to_days(total_man_hours) - 1)
        last_dates[task.id] = task.start_date

        if task.dependencies:
            deps_dates = [last_dates[dep] for dep in task.dependencies if dep in last_dates]
            if deps_dates:
                end_date = min(deps_dates) - datetime.timedelta(days=1)


    return tasks


def calculate_total_workdays(start_date, end_date):
    total_days = (end_date - start_date).days
    workdays = 0
    current_date = start_date

    for _ in range(total_days + 1):
        if Calendar.is_business_day(current_date):
            workdays += 1
        current_date += datetime.timedelta(days=1)

    return workdays

def get_new_start_date(end_date, total_workdays):
    current_date = end_date
    workdays_counted = 0

    while workdays_counted < total_workdays:
        if Calendar.is_business_day(current_date):
            workdays_counted += 1
        current_date -= datetime.timedelta(days=1)

    return current_date

def main_with_new_start():
    tasks = [
        Task("1", 16),
        Task("2", 40, dependencies=["1"]),
        Task("3", 24, dependencies=["2"]),
        Task("4", 24, dependencies=["3"]),
        Task("5", 12, dependencies=["4"]),
        Task("6", 80, dependencies=["5"]),
        Task("7", 64, dependencies=["2"]),
        Task("8", 48, dependencies=["7"]),
        Task("9", 480, dependencies=["8"]),
        Task("10", 40, dependencies=["9"]),
        Task("11", 24, dependencies=["6","10"])
    ]
#kokoko
    start_date = datetime.date(2023, 4, 1)
    scheduled_tasks = schedule_tasks(tasks, start_date)

    total_workdays = calculate_total_workdays(tasks[0].start_date, tasks[-1].end_date)
    desired_end_date = datetime.date(2024, 7, 1)
    new_start_date = get_new_start_date(desired_end_date, total_workdays)

    # Recalculate using the new start date
    tasks_new_start =[
        Task("1", 16),
        Task("2", 40, dependencies=["1"]),
        Task("3", 24, dependencies=["2"]),
        Task("4", 24, dependencies=["3"]),
        Task("5", 12, dependencies=["4"]),
        Task("6", 80, dependencies=["5"]),
        Task("7", 64, dependencies=["2"]),
        Task("8", 48, dependencies=["7"]),
        Task("9", 480, dependencies=["8"]),
        Task("10", 40, dependencies=["9"]),
        Task("11", 24, dependencies=["6","10"])
    ]
    scheduled_tasks_new_start = schedule_tasks(tasks_new_start, new_start_date)
    for task in scheduled_tasks_new_start:
        print(f"Task {task.id} - Start: {task.start_date}, End: {task.end_date}")


def generate_excel(tasks):
    """タスクのリストをエクセルファイルに出力する関数"""
    df = pd.DataFrame([(task.id, task.start_date, task.end_date) for task in tasks], columns=['Task', 'Start', 'Finish'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Schedule', index=False)
    return output.getvalue()



def create_gantt_chart(tasks):
    """ガントチャートの作成"""
    df = pd.DataFrame([(int(task.id), task.start_date, task.end_date) for task in tasks], columns=['Task', 'Start', 'Finish'])

    # タスクの名前を日本語に変更
    task_name_mapping = {
        1: "1: 田植え準備",
        2: "2: 耕起（田起こし",
        3: "3: 畦塗り",
        4: "4: 基肥",
        5: "5: 入水",
        6: "6: 代掻き",
        7: "7: 種籾準備",
        8: "8: 苗代の準備",
        9: "9: 播種",
        10: "10: 育苗管理",
        11: "11: 田植え"
    }
    df['農作業'] = df['Task'].map(task_name_mapping)

    # タスクIDで昇順にソート
    df = df.sort_values(by='Task', ascending=False)
    print(df)

    fig = px.timeline(df, x_start="Start", x_end="Finish", y="農作業", title="タスクスケジュール")
    #fig.update_yaxes(categoryorder="total ascending")

    # x軸のメモリを細かく設定
    fig.update_xaxes(
        tickmode='auto',  # メモリを自動調整
        nticks=20,  # メモリの数を増やす
        tickformat="%Y-%m-%d"  # YYYY-MM-DDの形式で表示
    )
    fig.update_layout(height=600, width=800)

    return fig


def draw_dependency_graph(task_order, previous_tasks_input):
    G = nx.DiGraph()
    
    for task_id in task_order:
        G.add_node(task_id, label=task_name_mapping[task_id])
        for prev_task_id in previous_tasks_input[task_id]:
            G.add_edge(prev_task_id, task_id)
    
    pos = nx.spring_layout(G)
    plt.figure(figsize=(10, 6))
    nx.draw(G, pos, with_labels=True, labels=nx.get_node_attributes(G, 'label'), node_size=3000, node_color="skyblue",font_family='Hiragino Kaku Gothic Pro')
    plt.title("タスクの依存関係")
    
    return plt

def main():
    st.markdown("# 🌾 稲作スケジュール作成")

    default_task_hours = {  # この辞書に各タスクのデフォルトの作業時間を設定
            "1": 1.0,
            "2": 30.0,
            "3": 10.0,
            "4": 10.0,
            "5": 10.0,
            "6": 30.0,
            "7": 10.0,
            "8": 10.0,
            "9": 10.0,
            "10": 30.0,
            "11": 30.0
        }
    # デフォルトの前のタスクのマッピングを設定
    default_previous_tasks = {
        "1": [],
        "2": ["1"],
        "3": ["2"],
        "4": ["3"],
        "5": ["4"],
        "6": ["5"],
        "7": ["1"],
        "8": ["7"],
        "9": ["8"],
        "10": ["9"],
        "11": ["6", "10"]
    }


    # サイドバーに入力部分を移動
    with st.sidebar:
        st.title("設定")
        field_area = st.number_input("圃場の面積を入力してください（デフォルト: 1ha）:", value=1.0, step=0.1)
        task_hours_input = {}
        buffer_input = {}
        max_workers_input = {}
        for task_id, task_name in task_name_mapping.items():
            task_hours_input[task_id] = st.number_input(
                f"{task_name} の作業時間を入力してください (時間/ha)：",
                value=default_task_hours[task_id],
                step=0.5  # ここで0.5単位での入力を設定
            )
            buffer_input[task_id] = st.number_input(f"{task_name} のバッファ日数を入力してください:", value=0, min_value=0, format="%d")
            max_workers_input[task_id] = st.number_input(f"{task_name} の同時稼働できるトラクタ/作業員の数を入力してください:", value=1, min_value=1, format="%d")

 


    tasks = [
        Task(task_id, task_hours_input[task_id], field_area, max_workers_input[task_id], buffer_input[task_id], dependencies=dependencies)
        for task_id, dependencies in [("1", []), ("2", ["1"]), ("3", ["2"]), ("4", ["3"]), ("5", ["4"]), ("6", ["5"]), ("7", ["1"]), ("8", ["7"]), ("9", ["8"]), ("10", ["9"]), ("11", ["6","10"])]
    ]


    # 作業IDから作業名へのマッピングを作成
    task_id_to_name = {id: name for id, name in task_name_mapping.items()}
    # 作業名から作業IDへのマッピングを作成
    task_name_to_id = {name: id for id, name in task_name_mapping.items()}

    # サイドバーにタスク順序の選択を追加
    with st.sidebar:
        if st.button("タスクのリセット"):
            task_hours_input = default_task_hours.copy()
            task_order_names = list(task_name_mapping.values())
            previous_tasks_input = default_previous_tasks.copy()
            st.success("タスクの順序と前のタスクの設定がデフォルトにリセットされました。")
    

        st.title("タスク順序")
        task_order_names = st.multiselect(
            "タスクの順序をドラッグ&ドロップで並べ替えてください:",
            list(task_name_mapping.values()),  # 作業名を使用
            default=list(task_name_mapping.values())  # デフォルト値も作業名を使用
        )
        # 選択された作業名を作業IDに変換
        task_order = [task_name_to_id[name] for name in task_order_names]
 

    # サイドバーにタスクの前のタスクの入力部分を追加
    with st.sidebar:
        st.title("前のタスク")
        previous_tasks_input = {}
        for task_id, task_name in task_name_mapping.items():
            # 選択された前のタスクの作業名を取得
            selected_prev_task_names = st.multiselect(
                f"{task_name} の前に完了する必要があるタスクを選択してください:",
                list(task_name_mapping.values()),
                default=[task_name_mapping[prev_task_id] for prev_task_id in default_previous_tasks[task_id]]
            )
            # 選択された前のタスクの作業名を作業IDに変換
            previous_tasks_input[task_id] = [task_name_to_id[name] for name in selected_prev_task_names]
        st.title("タスクの依存関係図")
        fig = draw_dependency_graph(task_order, previous_tasks_input)
        st.pyplot(fig)

    # タスクリストの生成
    tasks = [
        Task(task_id, task_hours_input[task_id], field_area, max_workers_input[task_id], buffer_input[task_id], dependencies=previous_tasks_input[task_id])
        for task_id in task_order
    ]
    start_date = datetime.date(2023, 4, 1)
    due_date = st.date_input('希望納期を選択してください:', datetime.date(2024, 7, 1))

    # スケジュールの計算ボタンがクリックされたときの処理
    if st.button('スケジュールの計算'):
        with st.spinner("計算中..."):  # アニメーションを追加
            tasks = schedule_tasks(tasks, start_date)
            total_workdays = calculate_total_workdays(tasks[0].start_date, tasks[-1].end_date)
            new_start_date = get_new_start_date(due_date, total_workdays)
            scheduled_tasks_new_start = schedule_tasks(tasks, new_start_date)
        
        st.success("計算完了!")  # 成功メッセージの表示
        st.subheader("📅 タスクスケジュール")
        st.write("以下は計算されたスケジュールのガントチャートです。")
        st.plotly_chart(create_gantt_chart(scheduled_tasks_new_start))

        # Excelファイルをダウンロードするボタンの追加
        excel_data = generate_excel(scheduled_tasks_new_start)
        st.download_button(
            label="エクセルファイルとしてダウンロード",
            data=excel_data,
            file_name="schedule.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
if __name__ == "__main__":
    main()





