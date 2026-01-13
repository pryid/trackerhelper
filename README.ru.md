# trackerhelper

Набор утилит для работы с музыкальной дискографией, разложенной по папкам (например, `Albums/*` и `Singles/*`):

- **`dr.ps1`** — автоматизирует запуск **foobar2000** и измерение **Dynamic Range (DR)** для каждого релиза, сохраняя DR-логи в отдельную папку.
- **`trackerhelper`** — CLI-утилита для сканирования дискографии, подсчёта длительности и генерации BBCode-шаблонов; умеет подхватывать DR-отчёты `*_dr.txt` и (опционально) загружать `cover.jpg` на FastPic.

Документы для разработчиков:
- `docs/ARCHITECTURE.md`
- `docs/DATA_FLOW.md`
- `docs/CONTRIBUTING.md`

Структура кода:
- `trackerhelper/cli/` — парсинг CLI и команды
- `trackerhelper/app/` — оркестрация use-case сценариев
- `trackerhelper/domain/` — чистые модели и бизнес-логика
- `trackerhelper/infra/` — внешние инструменты и файловая система
- `trackerhelper/formatting/` — форматирование BBCode и вывода

## Требования

### `dr.ps1` (Windows)
> ⚠️ **Обязательно включи автосохранение DR-логов в foobar2000**, иначе `dr.ps1` не сможет дождаться файла лога.

- Windows 10/11
- PowerShell 5+ (или PowerShell 7+)
- Установленный **foobar2000** (обычный или portable)
- Установленный компонент **DR Meter** в foobar2000
- Включённая опция **автоматической записи лога DR** (иначе лог не появится)

> Если DR Meter сохраняет логи в другое место (глобальную папку), `dr.ps1` их не увидит, потому что ищет лог внутри папки релиза (или внутри staging-копии, если источник read-only).

### `trackerhelper` (Windows / Linux / macOS)
- Python **3.10+**
- `ffprobe` из состава **ffmpeg** (должен быть доступен в `PATH`)
- `requests` (нужен для загрузки обложек на FastPic в команде `release`, устанавливается вместе с пакетом)
- `rich` (красивый прогресс в CLI, устанавливается вместе с пакетом)

Проверка:
```bash
ffprobe -version
```

## Рекомендуемая структура папок

Пример:

```text
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
- Группа определяется первым сегментом относительного пути (например `Albums`/`Singles`). Другие группы тоже поддерживаются и будут выведены отдельными заголовками.
- Релизом считается **любая папка, в которой найден хотя бы один поддерживаемый аудиофайл**.
- Год в имени папки релиза можно задавать как `Название - 2024` или `Название – 2024` — он будет использован в BBCode.

## Установка

```bash
pip install trackerhelper
```

Разработка из репозитория:
```bash
git clone https://github.com/pryid/trackerhelper
cd trackerhelper
pip install -e .
```

На Windows, если PowerShell запрещает запуск скриптов, можно разрешить для текущего пользователя:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Использование
Прогресс показывается только в TTY; отключить можно флагом `--no-progress`.

## 1) Автосбор DR-логов через foobar2000 (`dr.ps1`)

### Базовый запуск
```powershell
.\dr.ps1 -Root "D:\Music\Artist"
```

По умолчанию скрипт:
- ищет релизы в `Root\Albums\*` и `Root\Singles\*` (если такие группы есть),
- иначе считает релизами папки `Root\*`,
- копирует релиз в локальный staging только если источник read-only (например, SMB),
- запускает foobar2000 с context menu командой `Measure Dynamic Range`,
- ждёт появления лога `foo_dr*.txt|log` внутри папки релиза (или внутри staging, если источник read-only),
- копирует лог в папку отчётов.

### Где будут отчёты
Если не задан `-OutDir`, отчёты сохраняются в:
- `%USERPROFILE%\Music\DR`

Имя файла: `<имя_релиза>_dr.txt` (имя релиза берётся из имени папки; недопустимые символы заменяются на `_`).

### Если foobar2000 portable / не в стандартном месте
```powershell
.\dr.ps1 -Root "D:\Music\Artist" -FoobarPath "D:\Apps\foobar2000\foobar2000.exe"
```

### Часто используемые параметры
- `-Root` (**обязательный**) — корневая папка дискографии.
- `-FoobarPath` — путь к `foobar2000.exe` (если автопоиск не нашёл).
- `-CommandName` — **точное** имя команды из контекстного меню foobar (по умолчанию `"Measure Dynamic Range"`).
- `-Groups` — группы релизов (по умолчанию `Albums`, `Singles`).
- `-Ext` — расширения аудио (список).
- `-TimeoutSec` — максимальное ожидание лога на релиз (по умолчанию 1800 сек).
- `-LogNameRegex` — регулярка для имени лога (по умолчанию `^foo_dr.*\.(txt|log)$`).
- `-OutDir` — куда сохранять итоговые `*_dr.txt`.
- `-StageRoot` — где держать временные копии релизов (используется только для read-only источников).
- `-KeepStage` — не удалять staging (удобно для диагностики).
- `-ShowFoobar` — показывать окно foobar (иначе запускается minimized).

### Пример для источника read-only (SMB)
```powershell
.\dr.ps1 -Root "\\NAS\Music\Artist" -OutDir "D:\Reports\DR"
```

## 2) Подсчёт длительности/параметров + генерация BBCode (`trackerhelper`)

### Базовый запуск (группированный вывод)
```bash
trackerhelper stats "/path/to/DiscographyRoot"
```

Вывод по каждому релизу содержит:
- длительность
- количество треков (по файлам, у которых удалось прочитать duration)
- bit depth и sample rate (если ffprobe вернул значения)

В конце печатается суммарная строка `Total: ...`.

### Включить треки, лежащие прямо в корне
По умолчанию корень не считается релизом, чтобы не смешивать файлы. Если нужно — добавь `--include-root`:

```bash
trackerhelper stats "/path/to/DiscographyRoot" --include-root
```

### Добавить расширение (повторяемый параметр)
```bash
trackerhelper stats "/path/to/DiscographyRoot" --ext .ape --ext .tak
```

### Машиночитаемый вывод
```bash
trackerhelper stats "/path/to/DiscographyRoot" --json
trackerhelper stats "/path/to/DiscographyRoot" --csv
```

### Потрековый вывод
```bash
trackerhelper stats "/path/to/DiscographyRoot" --json --per-track
trackerhelper stats "/path/to/DiscographyRoot" --csv --per-track
```

### Запись вывода в файл
```bash
trackerhelper stats "/path/to/DiscographyRoot" --json --output "/tmp/stats.json"
```
Файлы вывода должны быть вне папки с музыкой.

### Нормализация имён папок релизов
По умолчанию выполняется "сухой" прогон (без переименований):

```bash
trackerhelper normalize "/path/to/DiscographyRoot"
```

Чтобы применить изменения:

```bash
trackerhelper normalize "/path/to/DiscographyRoot" --apply
```

Форматы:
- один релиз: `Artist - Album (Year)`
- несколько релизов: `Year - Artist - Album`

Важно: в команде `normalize` данные берутся из **тегов аудиофайлов** (album/artist), а год — из имени папки. Если теги/год отсутствуют, папка будет пропущена.

### Генерация BBCode-шаблона дискографии
```bash
trackerhelper release "/path/to/DiscographyRoot"
```

По умолчанию BBCode-лейблы на русском. Для английской версии:
```bash
trackerhelper release "/path/to/DiscographyRoot" --lang en
```

Отключить загрузку обложек на FastPic:
```bash
trackerhelper release "/path/to/DiscographyRoot" --no-cover
```

Файл будет записан в **текущую рабочую директорию** как:
- `<имя_корневой_папки>.txt`

В шаблоне остаются плейсхолдеры `ROOT_COVER_URL`, `GENRE`, `Service`, `YEAR`.
В русской версии используется `ЛЕЙБЛ`, в английской — `LABEL`.

### Куда писать BBCode
```bash
trackerhelper release "/path/to/DiscographyRoot" --output "/tmp/release.txt"
```
Файлы вывода должны быть вне папки с музыкой.

### Отчёт о недостающих обложках / DR логах
```bash
trackerhelper release "/path/to/DiscographyRoot" --report-missing
trackerhelper release "/path/to/DiscographyRoot" --report-missing "/tmp/missing_report.txt"
```
Файлы вывода должны быть вне папки с музыкой.

### Подстановка DR-отчётов в BBCode
Если у тебя уже есть `*_dr.txt` (например, собранные `dr.ps1`), укажи папку с логами:

```bash
trackerhelper release "/path/to/DiscographyRoot" --dr-dir "C:\Users\<you>\Music\DR"
```

Скрипт пытается сопоставить DR-файл с папкой релиза по имени (несколько вариантов имён + нормализация пробелов/дефисов). Если отчёт не найден — в BBCode остаётся `info`.

### Автоподстановка обложек через FastPic (опционально)
Если в папке релиза лежит `cover.jpg` (регистр неважен), то в команде `release` утилита загрузит обложку на FastPic и подставит прямую ссылку в BBCode. Если обложка не найдена или загрузка не удалась — остаётся `COVER_URL`.

## 3) Режим проверки форматирования без ffprobe/ФС (`--synthetic`)
```bash
trackerhelper stats "/any/path" --synthetic
trackerhelper release "/any/path" --synthetic
```

## 4) Поиск дублей релизов по аудио-отпечаткам (`trackerhelper dedupe`)
```bash
trackerhelper dedupe --roots Albums Singles
```

Опции:
- `--move-to DIR` — переместить найденные релизы в указанную папку
- `--delete` — удалить найденные релизы (опасно)
- `--json` — вывести JSON в stdout
- `--csv` — вывести CSV в stdout
- `--jsonl` — вывести JSON Lines в stdout
- `--output PATH` — записать JSON/CSV/JSONL в файл
- `--plan-out PATH` — сохранить план в JSON
- `--apply-plan PATH` — применить ранее сохраненный план
- `--dry-run` — не удалять/не перемещать релизы

Примечание: `--apply-plan` требует `--move-to` или `--delete`.
Файлы вывода и отчёты должны быть вне сканируемых корней.

`--synthetic` использует данные из `trackerhelper/app/synthetic_dataset.py` и позволяет быстро проверить, как выглядит консольный вывод и BBCode, не имея реальных файлов.

## Troubleshooting

### `dr.ps1`: лог не появляется
Чаще всего причина одна из двух:
- в DR Meter не включено автосохранение логов;
- DR Meter сохраняет логи не в папку релиза (а в другое место).

Для диагностики:
```powershell
.\dr.ps1 -Root "D:\Music\Artist" -LogNameRegex ".*\.(txt|log)$" -KeepStage
```
После этого проверь, какие файлы создаются в папке релиза (или в staging, если источник read-only).

### `dr.ps1`: “не нашёл foobar2000.exe”
Передай путь вручную:
```powershell
.\dr.ps1 -Root "D:\Music\Artist" -FoobarPath "D:\Apps\foobar2000\foobar2000.exe"
```

### `trackerhelper`: `Error: ffprobe not found`
Установи ffmpeg и добавь его в `PATH`, чтобы команда `ffprobe` запускалась из терминала.

### `trackerhelper`: bit depth / sample rate = `unknown` или `mixed`
Это нормально:
- некоторые форматы/файлы не содержат нужных полей, или ffprobe их не возвращает;
- внутри релиза могут быть разные параметры → `mixed`.
