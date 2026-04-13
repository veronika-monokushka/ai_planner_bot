# ИИ-Ежедневник


> 💡 **Технологии**: Python + FastAPI + GigaChat/Mistral_AI + SQLite/PostgreSQL


## 🗂️ Структура папок

```
ai_planner_bot/
├── src/
│   ├── bot.py                          # Главный файл запуска
│   ├── bot_backend/
│   │   ├── __init__.py
│   │   ├── config.py                   # Конфигурация (токен, настройки)
│   │   ├── states.py                   # Состояния ConversationHandler
│   │   ├── keyboards.py                # Клавиатуры бота
│   │   └── handlers/
│   │       ├── __init__.py
│   │       ├── common.py               # Навигация, главное меню
│   │       ├── registration.py         # Регистрация пользователя
│   │       ├── profile.py              # Профиль и его редактирование
│   │       ├── nutrition.py            # Питание, план на неделю
│   │       ├── recipes.py              # Рецепты (CRUD + поиск)
│   │       ├── reminders.py            # Напоминания
│   │       ├── weighing.py             # Взвешивание
│   │       ├── shopping.py             # Список покупок
│   │       └── utils.py                # Вспомогательные функции (recalculate_profile)
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py               # Подключение к БД
│   │   ├── users.py                    # Работа с пользователями
│   │   ├── recipes.py                  # Работа с рецептами
│   │   ├── meal_plans.py               # Работа с планами питания
│   │   ├── shopping_lists.py           # Работа со списками покупок
│   │   └── reminders.py                # Работа с напоминаниями
│   └── ai_agent/
│       ├── __init__.py
│       ├── agent_class.py               # Клиент для Mistral AI
│       ├── agent_class.py               
│       ├── meals_generator.py          # Генерация планов питания через AI
│       └── fallback_answers.py         # Fallback-планы и списки


Идеал

ai_planner_bot/
├── src/
│   ├── main.py                         # Точка входа (переименовать из bot.py)
│   ├── bot_connection/
│   │   ├── __init__.py
│   │   ├── application.py              # Сборка Application (регистрация обработчиков)
│   │   ├── config.py                   # Конфигурация
│   │   ├── states.py                   # Состояния
│   │   └── keyboards.py                # Клавиатуры - СТРАННО
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── base.py                     # Базовый класс для обработчиков
│   │   ├── navigation.py               # Навигация (бывший common.py)
│   │   ├── registration.py             # Регистрация
│   │   ├── profile.py                  # Профиль
│   │   ├── nutrition.py                # Питание (только UI логика)
│   │   ├── recipes.py                  # Рецепты
│   │   ├── reminders.py                # Напоминания
│   │   ├── weighing.py                 # Взвешивание
│   │   ├── shopping.py                 # Список покупок
│   │   └── utils.py                    # Вспомогательные функции
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py               # Подключение к БД
│   │   ├── users.py                    # Работа с пользователями
│   │   ├── recipes.py                  # Работа с рецептами
│   │   ├── meal_plans.py               # Работа с планами питания
│   │   ├── shopping_lists.py           # Работа со списками покупок
│   │   └── reminders.py                # Работа с напоминаниями
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py               # Сервис для AI (вызовы)
│   │   ├── calculator.py               # Расчеты (ИМТ, калории)
│   │   └── scheduler.py                # Планировщик напоминаний
│   └── utils/
│       ├── __init__.py
│       ├── formatters.py               # Форматирование текста
│       └── validators.py               # Валидация ввода
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

