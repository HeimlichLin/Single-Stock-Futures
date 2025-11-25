import PyInstaller.__main__
import os

# 確保在腳本所在目錄執行
os.chdir(os.path.dirname(os.path.abspath(__file__)))

PyInstaller.__main__.run([
    'app.py',                         # 主程式入口
    '--name=SingleStockFutures',      # 產生的 exe 名稱
    '--onefile',                      # 打包成單一檔案
    '--add-data=templates;templates', # 將 templates 資料夾加入 (Windows 使用 ;)
    # '--noconsole',                  # 若不想看到黑底終端機視窗，請取消此行註解 (但在除錯階段建議保留)
    '--clean',
])
