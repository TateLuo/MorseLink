import sqlite3
import json
import os

class DatabaseTool:
    def __init__(self, db_name='database.db', db_dir='resources/database'):
        self.db_name = os.path.join(db_dir, db_name)
        self.connection = None
        self.cursor = None
        self.initialize_database()

    def initialize_database(self):
        # 创建数据库目录（如果不存在）
        db_directory = os.path.dirname(self.db_name)
        os.makedirs(db_directory, exist_ok=True)

        # 检查数据库文件是否存在
        if os.path.exists(self.db_name):
            try:
                # 尝试连接数据库以检查其完整性
                self.connection = sqlite3.connect(self.db_name)
                self.cursor = self.connection.cursor()
                self.cursor.execute('SELECT name FROM sqlite_master WHERE type="table";')
                # 如果能成功执行查询，说明数据库正常
            except sqlite3.DatabaseError:
                # 如果发生数据库错误，说明数据库可能损坏
                print("数据库文件损坏，正在删除...")
                self.close()  # 确保关闭连接
                os.remove(self.db_name)  # 删除损坏的数据库文件
                self.connection = sqlite3.connect(self.db_name)  # 重新创建数据库
                self.cursor = self.connection.cursor()
        else:
            # 数据库文件不存在，创建新的数据库
            self.connection = sqlite3.connect(self.db_name)
            self.cursor = self.connection.cursor()

        # 检查表是否存在，如果不存在则创建
        self.check_and_create_tables()


    def check_and_create_tables(self):
        # 创建 QSOrecord 表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS QSOrecord (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                json_data TEXT NOT NULL
            )
        ''')
        
        # 创建 listening_lesson 表，并设置 status 和 progress 的默认值为 0
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS listening_lesson (
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                note TEXT,
                status INTEGER DEFAULT 0,
                progress INTEGER DEFAULT 0
            )
        ''')
        
        self.connection.commit()
        print("表 QSOrecord 和 listening_lesson 创建成功（如果不存在）。")


    def create_table(self):
        # 创建 QSOrecord 表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS QSOrecord (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                json_data TEXT NOT NULL
            )
        ''')
        
        # 创建 listening_lesson 表，并设置 status 和 progress 的默认值为 0
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS listening_lesson (
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                note TEXT,
                status INTEGER DEFAULT 0,
                progress INTEGER DEFAULT 0
            )
        ''')
        
        self.connection.commit()
        print("表 QSOrecord 和 listening_lesson 创建成功（如果不存在）。")

    def write_qso_record(self, data):
        # 写入数据
        json_data = json.dumps(data)
        self.cursor.execute('INSERT INTO QSOrecord (json_data) VALUES (?)', (json_data,))
        self.connection.commit()
        print("数据写入数据库成功。")

    def read_qso_record(self):
        # 读取数据
        self.cursor.execute('SELECT id, json_data FROM QSOrecord')
        rows = self.cursor.fetchall()
        data = [{"id": row[0], "data": json.loads(row[1])} for row in rows]
        return data
    
    def delete_qso_record_by_id(self, record_id):
        # 删除数据
        self.cursor.execute('DELETE FROM QSOrecord WHERE id = ?', (record_id,))
        self.connection.commit()
        print(f"ID 为 {record_id} 的记录已删除。")

    def close(self):
        # 关闭数据库连接
        if self.connection:
            self.connection.close()
            print("数据库连接已关闭。")

    def get_listening_lessons_by_type(self, lesson_type):
        """根据类型获取整行数据"""
        self.cursor.execute('SELECT * FROM listening_lesson WHERE type = ?', (lesson_type,))
        rows = self.cursor.fetchall()
        #print(rows)
        data = [{"title": row[0], "type": row[1], "content": row[2], "note": row[3], "status": row[4], "progress": row[5]} for row in rows]
        return data

    def update_status_by_title(self, title, new_status):
        """根据标题修改 status"""
        self.cursor.execute('UPDATE listening_lesson SET status = ? WHERE title = ?', (new_status, title))
        self.connection.commit()
        print(f"标题为 '{title}' 的记录状态已更新为 {new_status}。")

    def update_progress_by_title(self, title, new_progress):
        """根据标题修改 progress"""
        self.cursor.execute('UPDATE listening_lesson SET progress = ? WHERE title = ?', (new_progress, title))
        self.connection.commit()
        print(f"标题为 '{title}' 的记录进度已更新为 {new_progress}。")

    def get_progress_by_title(self, title):
        """根据标题获取 progress"""
        self.cursor.execute('SELECT progress FROM listening_lesson WHERE title = ?', (title,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        else:
            print(f"未找到标题为 '{title}' 的记录。")
            return None

    def get_status_by_title(self, title):
        """根据标题获取 status"""
        self.cursor.execute('SELECT status FROM listening_lesson WHERE title = ?', (title,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        else:
            print(f"未找到标题为 '{title}' 的记录。")
            return None
# 使用示例
if __name__ == "__main__":
    db_tool = DatabaseTool()

    # 写入数据示例
    sample_data = {"key": "value", "number": 42}
    db_tool.write_qso_record(sample_data)

    # 读取数据示例
    records = db_tool.read_qso_record()
    print("读取的记录:", records)

    # 关闭数据库
    db_tool.close()
