# README

## Описание

Проект — набор утилит для работы с музыкальной дискографией, разложенной по папкам (например `Albums/*` и `Singles/*`):

- **`dr.ps1`**: автоматизирует запуск **foobar2000** и измерение **Dynamic Range (DR)** для каждого релиза, сохраняя DR-логи в удобное место. Скрипт умеет работать с источником на **read-only** (например SMB-шара): он копирует релиз во временную локальную папку (“staging”), чтобы компонент DR смог записать лог.
- **`main.py`**: сканирует папку дискографии, считает суммарную длительность по каждому релизу, определяет sample rate/bit depth через **ffprobe**, и (опционально) генерирует BBCode шаблон релиза/дискографии. Также может подтягивать DR-отчёты `*_dr.txt` и вставлять их в шаблон.

---

## Возможности

### `dr.ps1` (Windows / foobar2000)
- Поиск релизов в `Root/Albums/*` и `Root/Singles/*` (или напрямую в `Root/*`, если групп нет).
- Поиск аудио-файлов по расширениям (настраиваемо).
- Копирование релиза в локальный staging (важно для read-only источников).
- Запуск foobar2000 с нужной **context menu** командой (по умолчанию `Measure Dynamic Range`).
- Ожидание появления лога (`foo_dr*.txt|log` по умолчанию) с таймаутом.
- Сохранение итогового лога как `<релиз>_dr.txt` в папку отчётов.

### `main.py` (кроссплатформенно, Python + ffprobe)
- Рекурсивно находит аудио внутри папок релизов.
- Считает:
  - длительность на релиз и общую длительность
  - количество треков
  - sample rate (kHz) и bit depth (bit) (если доступно)
  - тип кодека по расширениям
- Группирует вывод по `Albums`/`Singles` (можно сделать “плоско”).
- `--release`: генерирует BBCode шаблон (удобно для форумных релизов/постов).
- `--dr`: подхватывает DR-логи и вставляет их в BBCode.

---

## Требования

### Для `dr.ps1`

⚠️ **Обязательно включи автосохранение DR-логов в foobar2000**, иначе `dr.ps1` не сможет дождаться файла лога.

Путь в настройках:
- `File → Preferences → Advanced → DR Meter → Automatically save logs` (поставь галочку)

- Windows 10/11
- PowerShell 5+ (или PowerShell 7+)
- Установленный **foobar2000** (обычный или portable)
- Установленный компонент/плагин DR Meter (в foobar2000)
- Включённая опция **автоматической записи лога DR** (иначе лог не появится)

### Для `main.py`
- Python 3.10+ (или близко)
- **ffprobe** из состава ffmpeg (обязателен — скрипт проверяет наличие `ffprobe` в PATH и завершится с ошибкой, если его нет)

---

## Рекомендуемая структура папок

Пример:

```
DiscographyRoot/
  Albums/
    Album Name - 2019/
      01 - Track.flac
      02 - Track.flac
    Another Album - 2021/
      ...
  Singles/
    Single Name - 2020/
      ...
```

Подсказки:
- Годы можно указывать в имени папки релиза — `main.py` пытается распарсить формат `Название - 2024`.
- Если `Albums/` и `Singles/` отсутствуют — `dr.ps1` будет считать, что релизы лежат напрямую в корне.

---

## Установка

### 1) Клонировать проект
```
git clone <repo_url>
cd <repo_folder>
```

### 2) Установить ffmpeg (для `main.py`)
Убедись, что `ffprobe` доступен в PATH:

- Windows:
  ```
  ffprobe -version
  ```
- Linux/macOS:
  ```
  ffprobe -version
  ```

### 3) Разрешить запуск PowerShell-скриптов (Windows)
При необходимости (осторожно в корпоративной среде):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Использование

## 1) Автосбор DR логов через foobar2000 (`dr.ps1`)

### Базовый запуск
```powershell
.\dr.ps1 -Root "D:\Music\Artist"
```

Скрипт:
- найдёт релизы,
- скопирует каждый релиз во временную локальную папку,
- запустит foobar2000 с `Measure Dynamic Range`,
- дождётся появления лога и сохранит его в `Music\DR` по умолчанию.

### Если foobar2000 portable / не в стандартном месте
```powershell
.\dr.ps1 -Root "D:\Music\Artist" -FoobarPath "D:\Apps\foobar2000\foobar2000.exe"
```

### Основные параметры
- `-Root` (обязательный): корневая папка дискографии.
- `-FoobarPath`: путь к `foobar2000.exe` (если не найден автоматически).
- `-CommandName`: **точное** имя команды из контекстного меню foobar (по умолчанию `"Measure Dynamic Range"`).
- `-Groups`: группы релизов (по умолчанию `Albums`, `Singles`).
- `-Ext`: расширения аудио (список).
- `-TimeoutSec`: сколько ждать появления лога на релиз.
- `-LogNameRegex`: регэксп имени лога (по умолчанию `^foo_dr.*\.(txt|log)$`).
- `-OutDir`: куда складывать итоговые `*_dr.txt`.
- `-StageRoot`: куда складывать временные копии релизов.
- `-KeepStage`: не удалять staging (для дебага).
- `-ShowFoobar`: показывать окно foobar (иначе minimized).

---

## 2) Подсчёт длительности/параметров + генерация BBCode (`main.py`)

### Базовый запуск (группированный вывод)
```bash
python main.py "/path/to/DiscographyRoot"
```

Скрипт выведет по каждому релизу:
- длительность
- число треков
- bit depth и sample rate (если ffprobe смог прочитать)

И затем `Total: ...`.

### Плоский вывод без заголовков групп
```bash
python main.py "/path/to/DiscographyRoot" --flat
```

### Добавить расширение
```bash
python main.py "/path/to/DiscographyRoot" --ext .ape
```

### Генерация BBCode шаблона релиза/дискографии
```bash
python main.py "/path/to/DiscographyRoot" --release
```

Шаблон будет записан в файл:
- `/tmp/<имя_корневой_папки>` (без расширения)

### Вставка DR отчётов в BBCode (если у тебя уже есть `*_dr.txt`)
Например, если `dr.ps1` сохранил логи в `C:\Users\<you>\Music\DR`:

```bash
python main.py "D:\Music\Artist" --release --dr "C:\Users\<you>\Music\DR"
```

Скрипт попробует сопоставить DR файл с релизом по имени папки (есть несколько вариантов имён + “нормализация”).

---

## Типичный пайплайн

1) Сначала собрать DR логи (Windows):
```powershell
.\dr.ps1 -Root "D:\Music\Artist"
```

2) Потом сгенерировать BBCode, подтянув DR:
```bash
python main.py "D:\Music\Artist" --release --dr "C:\Users\<you>\Music\DR"
```

---

## Troubleshooting

### `dr.ps1`: “Лог не появился…”
Чаще всего это означает, что в DR Meter/компоненте **не включено автосохранение логов**.

Включи:
- `File → Preferences → Advanced → DR Meter → Automatically save logs` (галочка)

Затем повтори запуск.

Для диагностики можно расширить маску:
```powershell
.\dr.ps1 -Root "D:\Music\Artist" -LogNameRegex ".*\.(txt|log)$" -KeepStage
```
и посмотреть, какие файлы реально создаются в staging.

### `dr.ps1`: команда не запускается / не тот пункт меню
Убедись, что `-CommandName` совпадает **строго** с названием команды контекстного меню foobar.

### `main.py`: `Error: ffprobe not found`
Установи ffmpeg и добавь его в PATH так, чтобы команда `ffprobe` была доступна из терминала.

### `main.py`: bit depth / sample rate = unknown / mixed
Это нормально:
- некоторые форматы/файлы не содержат `bits_per_sample` в метаданных, или ffprobe не всегда это возвращает;
- внутри релиза могут быть разные частоты/битности → будет `mixed`.

---
