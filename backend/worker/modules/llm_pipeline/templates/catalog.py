from backend.worker.modules.llm_pipeline.templates.template import TemplateBlock, Template

TEMPLATES: dict[str, Template] = {
    "it_001": Template(
        template_id="it_001",
        name="IT-проект",
        domain="it",
        version="1.0",
        description="Для продуктовой разработки. Фокус на ролях, сценариях, стеке.",
        blocks=[
            TemplateBlock(
                template_block_id="it_intro",
                title="Общее описание проекта",
                level=1, sort_order=0,
                context_hint="Название проекта, цели, заказчик, краткое описание продукта",
                subsections=[
                    TemplateBlock(
                        template_block_id="it_intro_purpose",
                        title="Назначение системы",
                        level=2, sort_order=0,
                        context_hint="Для кого система, какую проблему решает, целевая аудитория",
                    ),
                    TemplateBlock(
                        template_block_id="it_intro_glossary",
                        title="Термины и сокращения",
                        level=2, sort_order=1,
                        context_hint="Специфические термины, аббревиатуры, упомянутые в источниках",
                        required=False,
                    ),
                ],
            ),
            TemplateBlock(
                template_block_id="it_func",
                title="Функциональные требования",
                level=1, sort_order=1,
                context_hint="Функции системы, бизнес-логика, пользовательские сценарии",
                subsections=[
                    TemplateBlock(
                        template_block_id="it_func_roles",
                        title="Пользовательские роли",
                        level=2, sort_order=0,
                        context_hint="Роли пользователей: admin, user, guest — их права и сценарии",
                    ),
                    TemplateBlock(
                        template_block_id="it_func_usecases",
                        title="Пользовательские сценарии (Use Cases)",
                        level=2, sort_order=1,
                        context_hint="Конкретные сценарии использования, user stories, флоу",
                    ),
                ],
            ),
            TemplateBlock(
                template_block_id="it_tech",
                title="Технические требования",
                level=1, sort_order=2,
                context_hint="Стек технологий, архитектура, нефункциональные требования",
                subsections=[
                    TemplateBlock(
                        template_block_id="it_tech_stack",
                        title="Стек технологий",
                        level=2, sort_order=0,
                        context_hint="Языки, фреймворки, СУБД, очереди, облако — все упомянутые технологии",
                    ),
                    TemplateBlock(
                        template_block_id="it_tech_nfr",
                        title="Нефункциональные требования",
                        level=2, sort_order=1,
                        context_hint="Производительность, доступность, безопасность, масштабируемость",
                    ),
                    TemplateBlock(
                        template_block_id="it_tech_integrations",
                        title="Интеграции",
                        level=2, sort_order=2,
                        context_hint="Внешние API, сервисы, системы с которыми нужна интеграция",
                        required=False,
                    ),
                ],
            ),
            TemplateBlock(
                template_block_id="it_timeline",
                title="Этапы и сроки",
                level=1, sort_order=3,
                context_hint="Дедлайны, этапы разработки, спринты, майлстоуны",
            ),
            TemplateBlock(
                template_block_id="it_acceptance",
                title="Критерии приёмки",
                level=1, sort_order=4,
                context_hint="Definition of Done, KPI, метрики успеха, приёмочное тестирование",
            ),
        ],
    ),

    "formal_001": Template(
        template_id="formal_001",
        name="Формальный (ГОСТ-like)",
        domain="formal",
        version="1.0",
        description="Строгий стиль для госзаказов и крупных корпораций.",
        blocks=[
            TemplateBlock(
                template_block_id="f_general",
                title="Общие положения",
                level=1, sort_order=0,
                context_hint="Юридическое основание, стороны договора, предмет ТЗ",
                subsections=[
                    TemplateBlock(
                        template_block_id="f_general_basis",
                        title="Основание для разработки",
                        level=2, sort_order=0,
                        context_hint="Номер договора, приказа, НПА — юридические документы-основания",
                    ),
                    TemplateBlock(
                        template_block_id="f_general_parties",
                        title="Стороны",
                        level=2, sort_order=1,
                        context_hint="Заказчик и исполнитель: названия организаций, ответственные лица",
                    ),
                ],
            ),
            TemplateBlock(
                template_block_id="f_scope",
                title="Назначение и цели",
                level=1, sort_order=1,
                context_hint="Цели системы, назначение, ожидаемый эффект",
            ),
            TemplateBlock(
                template_block_id="f_requirements",
                title="Требования к системе",
                level=1, sort_order=2,
                context_hint="Функциональные и технические требования в формальном стиле",
                subsections=[
                    TemplateBlock(
                        template_block_id="f_req_func",
                        title="Функциональные требования",
                        level=2, sort_order=0,
                        context_hint="Перечень функций системы в нумерованном формате",
                    ),
                    TemplateBlock(
                        template_block_id="f_req_tech",
                        title="Технические требования",
                        level=2, sort_order=1,
                        context_hint="Требования к оборудованию, ПО, среде эксплуатации",
                    ),
                    TemplateBlock(
                        template_block_id="f_req_security",
                        title="Требования к безопасности",
                        level=2, sort_order=2,
                        context_hint="Информационная безопасность, защита данных, доступы",
                    ),
                ],
            ),
            TemplateBlock(
                template_block_id="f_stages",
                title="Стадии и этапы разработки",
                level=1, sort_order=3,
                context_hint="Этапы работ, сроки каждого этапа, ответственные",
            ),
            TemplateBlock(
                template_block_id="f_acceptance",
                title="Порядок контроля и приёмки",
                level=1, sort_order=4,
                context_hint="Приёмочные испытания, акты, критерии соответствия",
            ),
        ],
    ),

    "free_001": Template(
        template_id="free_001",
        name="Свободный (Бытовой)",
        domain="free",
        version="1.0",
        description="Минималистичный формат для личных задач и небольших заказов.",
        blocks=[
            TemplateBlock(
                template_block_id="fr_what",
                title="Что нужно сделать",
                level=1, sort_order=0,
                context_hint="Суть задачи в свободной форме, конечный результат",
            ),
            TemplateBlock(
                template_block_id="fr_details",
                title="Детали и пожелания",
                level=1, sort_order=1,
                context_hint="Визуальные детали, материалы, размеры, стиль, предпочтения",
                subsections=[
                    TemplateBlock(
                        template_block_id="fr_details_materials",
                        title="Материалы",
                        level=2, sort_order=0,
                        context_hint="Из чего делать, какие материалы использовать или исключить",
                        required=False,
                    ),
                ],
            ),
            TemplateBlock(
                template_block_id="fr_result",
                title="Ожидаемый результат",
                level=1, sort_order=2,
                context_hint="Конкретные предметы/артефакты на выходе, как выглядит «готово»",
            ),
            TemplateBlock(
                template_block_id="fr_budget",
                title="Бюджет и сроки",
                level=1, sort_order=3,
                context_hint="Стоимость, дедлайн, ограничения по деньгам и времени",
                required=False,
            ),
        ],
    ),

    "construction_001": Template(
        template_id="construction_001",
        name="Строительный проект",
        domain="construction",
        version="1.0",
        description="Для СМР. Фокус на объёмах, материалах и актах скрытых работ.",
        blocks=[
            TemplateBlock(
                template_block_id="c_object",
                title="Описание объекта",
                level=1, sort_order=0,
                context_hint="Адрес, тип объекта, площадь, этажность, назначение",
            ),
            TemplateBlock(
                template_block_id="c_scope",
                title="Состав и объём работ",
                level=1, sort_order=1,
                context_hint="Перечень видов работ, объёмы в единицах измерения (м², м³, пог. м)",
            ),
            TemplateBlock(
                template_block_id="c_materials",
                title="Материалы",
                level=1, sort_order=2,
                context_hint="Материалы заказчика и подрядчика, спецификации, марки",
                subsections=[
                    TemplateBlock(
                        template_block_id="c_mat_customer",
                        title="Материалы заказчика",
                        level=2, sort_order=0,
                        context_hint="Что поставляет заказчик: наименование, количество, сроки поставки",
                    ),
                    TemplateBlock(
                        template_block_id="c_mat_contractor",
                        title="Материалы подрядчика",
                        level=2, sort_order=1,
                        context_hint="Что закупает подрядчик самостоятельно, требования к качеству",
                    ),
                ],
            ),
            TemplateBlock(
                template_block_id="c_hidden_works",
                title="Акты скрытых работ",
                level=1, sort_order=3,
                context_hint="Перечень работ, требующих актирования до закрытия: армирование, гидроизоляция",
            ),
            TemplateBlock(
                template_block_id="c_timeline",
                title="График производства работ",
                level=1, sort_order=4,
                context_hint="Этапы СМР, сроки начала и окончания каждого этапа",
            ),
        ],
    ),

    "engineering_001": Template(
        template_id="engineering_001",
        name="Инженерный проект",
        domain="engineering",
        version="1.0",
        description="Для проектирования узлов и механизмов. Фокус на ГОСТ и допусках.",
        blocks=[
            TemplateBlock(
                template_block_id="e_purpose",
                title="Назначение и область применения",
                level=1, sort_order=0,
                context_hint="Для чего узел/механизм, условия эксплуатации, отрасль",
            ),
            TemplateBlock(
                template_block_id="e_norms",
                title="Нормативная база",
                level=1, sort_order=1,
                context_hint="ГОСТ, СНиП, ТУ, стандарты — все упомянутые нормативные документы",
            ),
            TemplateBlock(
                template_block_id="e_params",
                title="Технические параметры",
                level=1, sort_order=2,
                context_hint="Физические характеристики: мощность, давление, температура, габариты",
                subsections=[
                    TemplateBlock(
                        template_block_id="e_params_main",
                        title="Основные параметры",
                        level=2, sort_order=0,
                        context_hint="Ключевые рабочие параметры с единицами измерения",
                    ),
                    TemplateBlock(
                        template_block_id="e_params_tolerances",
                        title="Допуски и посадки",
                        level=2, sort_order=1,
                        context_hint="Допустимые отклонения, квалитеты точности, классы посадок",
                    ),
                ],
            ),
            TemplateBlock(
                template_block_id="e_testing",
                title="Методики испытаний",
                level=1, sort_order=3,
                context_hint="Как проверять: стенды, методы контроля, приёмочные значения",
            ),
        ],
    ),
}