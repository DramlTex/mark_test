# Документация по переменным

В этом проекте используется скрипт `entrypoint.sh`, который опирается на ряд окружений и входных параметров. Ниже приведено описание основных переменных.

| Переменная | Где используется | Назначение |
|------------|-----------------|------------|
| `PR_NUMBER` | entrypoint.sh | Номер pull request'а. Если не задана явно, извлекается из события GitHub. |
| `GITHUB_EVENT_PATH` | entrypoint.sh | Путь к JSON-файлу с описанием события. |
| `GITHUB_TOKEN` | entrypoint.sh | Токен доступа к API GitHub для выполнения запросов и push-операций. |
| `MAX_RETRIES` | entrypoint.sh | Количество попыток проверить готовность PR к ребейзу (по умолчанию 6). |
| `RETRY_INTERVAL` | entrypoint.sh | Интервал ожидания между попытками в секундах (по умолчанию 10). |
| `INPUT_AUTOSQUASH` | entrypoint.sh, action.yml | Включает режим `git rebase --autosquash`, если значение равно `true`. |
| `USER_TOKEN` | entrypoint.sh | Если определена переменная `<логин>_TOKEN`, используется вместо `GITHUB_TOKEN` для авторства коммитов. |
| `COMMITTER_TOKEN` | entrypoint.sh | Токен после обработки пробелов; используется для push. |

Эти переменные задаются в workflow GitHub Actions или через окружение Docker.
