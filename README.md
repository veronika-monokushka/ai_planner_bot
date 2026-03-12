# ИИ-Ежедневник


> 💡 **Технологии**: Python + FastAPI + GigaChat/Mistral_AI + SQLite/PostgreSQL


## 🗂️ Структура папок

```
ai_daily_planner_bot/
├── src/                    # Основной код
│   ├── ai_agent/           # Промпты, логика нейросети
│   ├── bot_food_plan/      # Функции питания/фитнеса (для будущего расширения)
│   ├── bot_core.py         # Подключение к Telegram API, обработка команд

# на будущее
│   └── database/           # Модели базы данных
├── docs/                   # Документация проекта
├── docker/                 # Docker-контейнеры
├── .env/                   # (не коммитить!)
├── .gitignore              # Скрытые файлы 
├── README.md               # Этот файл
├── pyproject.toml          # Конфигурация проекта (настройки зависимостей)
└── requirements.txt        # Список библиотек (pip install)
```

---

## 🚀 Как начать работать с проектом

 Работа через платформу GitLab:

1. Зайдите в проект на [GitLab](https://gitlab.com/)
2. Перейдите в **Repository → Files**
3. Нажмите **Create new file** или **Add file → Create new file**
4. Введите имя файла и код → **Commit changes**
5. **Сохраняйте всё!**










## Примечания Гитлаба:

### Add your files

* [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
* [Add files using the command line](https://docs.gitlab.com/topics/git/add_files/#add-files-to-a-git-repository) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://intst.ru/monokushka/ai_planner_bot.git
git branch -M main
git push -uf origin main
```


### Integrate with your tools

* [Set up project integrations](https://intst.ru/monokushka/ai_planner_bot/-/settings/integrations)

### Collaborate with your team

* [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
* [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
* [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
* [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
* [Set auto-merge](https://docs.gitlab.com/user/project/merge_requests/auto_merge/)

### Test and Deploy

Use the built-in continuous integration in GitLab.

* [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/)
* [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
* [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
* [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
* [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***

