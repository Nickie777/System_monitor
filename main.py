import sys
import json
import psycopg2
from PyQt5 import QtWidgets, QtGui, QtCore


class DatabaseMonitorApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OUTSS Monitor")
        self.setGeometry(100, 100, 800, 600)

        # Load settings and jobs
        self.db_settings = self.load_settings()
        self.jobs = self.load_jobs()

        # Set up menu
        self.init_menu()

        # Создаем центральный виджет и компоновщик
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Set up monitor table
        self.monitor_table = QtWidgets.QTableWidget(self)
        self.monitor_table.setColumnCount(5)
        self.monitor_table.setHorizontalHeaderLabels(
            ["Активировать", "Наименование", "Результат", "Последний запуск", "Периодичность"])

        # Устанавливаем режим растягивания колонок
        self.monitor_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        # Добавляем таблицу в компоновщик
        layout.addWidget(self.monitor_table)

        # Timer for periodic job execution
        self.job_timers = {}

        # Load jobs into the table
        self.load_jobs_into_table()

    def init_menu(self):
        menu = self.menuBar()

        settings_menu = menu.addMenu("Настройки")
        add_job_menu = menu.addMenu("Добавить job")

        settings_action = QtWidgets.QAction("Настройки БД", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(settings_action)

        add_job_action = QtWidgets.QAction("Добавить новую задачу", self)
        add_job_action.triggered.connect(self.open_add_job_dialog)
        add_job_menu.addAction(add_job_action)

    def open_settings_dialog(self):
        dialog = DbSettingsDialog(self.db_settings)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.db_settings = dialog.get_settings()
            self.save_settings()

    def open_add_job_dialog(self):
        dialog = AddJobDialog()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            job_data = dialog.get_job_data()
            self.jobs.append(job_data)
            self.save_jobs()
            self.load_jobs_into_table()

    def load_jobs_into_table(self):
        self.monitor_table.setRowCount(len(self.jobs))
        for row, job in enumerate(self.jobs):
            # Activate checkbox
            activate_checkbox = QtWidgets.QCheckBox()
            activate_checkbox.stateChanged.connect(lambda state, r=row: self.toggle_job_execution(r, state))
            self.monitor_table.setCellWidget(row, 0, activate_checkbox)

            # Job name
            job_name_item = QtWidgets.QTableWidgetItem(job['name'])
            self.monitor_table.setItem(row, 1, job_name_item)

            # Success status (initially unknown)
            success_item = QtWidgets.QTableWidgetItem("Unknown")
            success_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.monitor_table.setItem(row, 2, success_item)

            # Last execution time
            last_exec_item = QtWidgets.QTableWidgetItem("")
            self.monitor_table.setItem(row, 3, last_exec_item)

            # Frequency
            frequency_item = QtWidgets.QTableWidgetItem(str(job['frequency']))
            frequency_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.monitor_table.setItem(row, 4, frequency_item)

    def toggle_job_execution(self, row, state):
        job = self.jobs[row]
        if state == QtCore.Qt.Checked:
            timer = QtCore.QTimer(self)
            timer.timeout.connect(lambda: self.execute_job(row))
            timer.start(job['frequency'] * 1000)
            self.job_timers[row] = timer
        else:
            self.job_timers[row].stop()
            del self.job_timers[row]

    def execute_job(self, row):
        job = self.jobs[row]
        success_item = self.monitor_table.item(row, 2)
        last_exec_item = self.monitor_table.item(row, 3)

        try:
            connection = psycopg2.connect(**self.db_settings)
            cursor = connection.cursor()
            cursor.execute(job['query'])
            result = cursor.fetchone()
            connection.close()

            if result and result[0] == True:
                success_item.setText("True")
                success_item.setBackground(QtGui.QColor("green"))
            elif result and result[0] == False:
                success_item.setText("False")
                success_item.setBackground(QtGui.QColor("red"))
            else:
                success_item.setText("Other")
                success_item.setBackground(QtGui.QColor("yellow"))

            last_exec_item.setText(QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss"))

        except Exception as e:
            success_item.setText(f"Error: {e}")
            success_item.setBackground(QtGui.QColor("red"))

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_settings(self):
        with open('settings.json', 'w') as f:
            json.dump(self.db_settings, f)

    def load_jobs(self):
        try:
            with open('jobs.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def save_jobs(self):
        with open('jobs.json', 'w') as f:
            json.dump(self.jobs, f)


class DbSettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings):
        super().__init__()
        self.setWindowTitle("Настройки БД")
        self.settings = settings

        layout = QtWidgets.QFormLayout(self)
        self.host_input = QtWidgets.QLineEdit(self.settings.get("host", ""))
        self.port_input = QtWidgets.QLineEdit(str(self.settings.get("port", "5432")))
        self.dbname_input = QtWidgets.QLineEdit(self.settings.get("dbname", ""))
        self.user_input = QtWidgets.QLineEdit(self.settings.get("user", ""))
        self.password_input = QtWidgets.QLineEdit(self.settings.get("password", ""))
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)

        layout.addRow("Host:", self.host_input)
        layout.addRow("Port:", self.port_input)
        layout.addRow("Database Name:", self.dbname_input)
        layout.addRow("User:", self.user_input)
        layout.addRow("Password:", self.password_input)

        buttons = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        button_box = QtWidgets.QDialogButtonBox(buttons)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_settings(self):
        return {
            "host": self.host_input.text(),
            "port": int(self.port_input.text()),
            "dbname": self.dbname_input.text(),
            "user": self.user_input.text(),
            "password": self.password_input.text(),
        }


class AddJobDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Добавить новую задачу")

        layout = QtWidgets.QFormLayout(self)
        self.name_input = QtWidgets.QLineEdit()
        self.description_input = QtWidgets.QLineEdit()
        self.query_input = QtWidgets.QTextEdit()
        self.frequency_input = QtWidgets.QSpinBox()
        self.frequency_input.setMinimum(1)

        layout.addRow("Наименование:", self.name_input)
        layout.addRow("Описание:", self.description_input)
        layout.addRow("Запрос:", self.query_input)
        layout.addRow("Периодичность (сек):", self.frequency_input)

        buttons = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        button_box = QtWidgets.QDialogButtonBox(buttons)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_job_data(self):
        return {
            "name": self.name_input.text(),
            "description": self.description_input.text(),
            "query": self.query_input.toPlainText(),
            "frequency": self.frequency_input.value(),
        }


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = DatabaseMonitorApp()
    window.show()
    sys.exit(app.exec_())
