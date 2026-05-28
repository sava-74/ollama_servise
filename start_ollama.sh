#!/bin/bash
# Управление демоном Ollama

# 1. Корректная остановка предыдущих инстансов
pkill -f "ollama serve" 2>/dev/null || true
sleep 1

# 2. Сетевая конфигурация
export OLLAMA_HOST="0.0.0.0:11434"
export OLLAMA_KEEP_ALIVE="-1" # Модель не выгружается из RAM/VRAM (опционально)

# 3. Запуск в фоне с логированием в папку репо
nohup ollama serve > "$(pwd)/ollama_daemon.log" 2>&1 &
echo "PID: $!"

# 4. Health-check (ожидание готовности API до 10 сек)
for i in {1..10}; do
  curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "[+] Сервер запущен. Доступен по сети."
    exit 0
  fi
  sleep 1
done
echo "[-] Ошибка инициализации. Смотри ollama_daemon.log"
exit 1