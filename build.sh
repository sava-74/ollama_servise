#!/bin/bash

# Остановка скрипта при любой ошибке
set -e

echo "[Шаг 1/3] Очистка директории dist от старых сборок..."
rm -rf build dist "Ollama Service.spec"

echo "[Шаг 2/3] Запуск компиляции PyInstaller..."
# --windowed: создает .app без терминала
# --icon: задает иконку приложения
# --name: имя выходного файла
pyinstaller --windowed --icon=icon.icns --name "Ollama Service" ollama_manager.py

echo "[Шаг 3/3] Ad-hoc подпись пакета (Ad-hoc Code Signing)..."
# codesign --force: перезаписать существующую подпись
# --deep: подписать все вложенные библиотеки и бинарники внутри .app
# --sign -: использовать временный локальный ключ (Ad-hoc)
codesign --force --deep --sign - "dist/Ollama Service.app"

echo "[Успех] Сборка завершена."
echo "Файл приложения находится в папке dist/Ollama Service.app"
echo "Приложение подписано и готово к работе в сети без настройки брандмауэра."