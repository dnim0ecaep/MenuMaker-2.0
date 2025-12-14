source myenv/bin/activate
pip install pyinstaller
pyinstaller --onefile menu-maker.py
sudo cp dist/menu-maker /usr/sbin
