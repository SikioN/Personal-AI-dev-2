import pytest

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.agents.AgentDriver import AgentDriverConfig, AgentConnectorConfig
from src.pipelines.memorize import MemPipelineConfig, LLMExtractorConfig, LLMUpdatorConfig
from src.pipelines.memorize.extractor.agent_tasks.thesis_extraction import AgentThesisExtrTaskConfigSelector
from src.pipelines.memorize.extractor.agent_tasks.triplet_extraction import AgentTripletExtrTaskConfigSelector
from src.db_drivers.kv_driver import KeyValueDriverConfig, KVDBConnectionConfig

# RAW_TEXTS_RU = [
#     "Проживающие в общежитии студенты имеют право rруглосуточного доступа к месту проживания.",
#     "Проживающие в общежитии студенты имеют право обратиться к администрации ФГБУ «МСГ» с заявлением, заверенным заведующим общежития, о размещении в гостевых комнатах общежития родственников (на короткий период пребывания, не менее 2-х суток), родителей - на любой срок (при предоставлении документа, подтверждающего степень родства).",
#     "Проживающие в общежитии студенты имеют право пользоваться помещениями для самостоятельных занятий и помещениями культурно-бытового назначения, оборудованием, инвентарем общежития.",
#     "Проживающие в общежитии студенты имеют право обращаться к администрации корпуса с просьбами о своевременном ремонте, замене оборудования и инвентаря, вышедшего из строя не по их вине.",
#     "Проживающие в общежитии студенты имеют право на переселение из одного помещения в другое в том же корпусе, а также на переселение из одного корпуса в другой при наличии свободных мест, с согласия администрации корпуса.",
#     "Проживающие в общежитии студенты имеют право участвовать в формировании и выборах Студенческого совета МСГ и быть избранным в его состав.",
#     "Проживающие в общежитии студенты имеют право участвовать (вносить предложения) через Студенческий совет МСГ и отдел по молодежной политике ФГБУ «МСГ» в решении вопросов совершенствования жилищно-бытовых условий, организации воспитательной работы и досуга.",
#     "Проживающие в общежитии студенты имеют право принимать участие в общественных, спортивных и культурно-досуговых мероприятиях, организованных администрацией ФГБУ «МСГ» и Студенческим советом МСГ.",
#     "Проживающие в общежитии студенты имеют право пользоваться разрешенной бытовой техникой с соблюдением правил техники безопасности и правил пожарной безопасности.",
#     "Проживающие в общежитии студенты имеют право бесплатно посещать Межвузовский  учебно-спортивный центр в утвержденное администрацией ФГБУ «МСГ» и согласованное со Студенческим советом МСГ время.",
#     "Проживающие в общежитии студенты имеют право бесплатно посещать душевой комплекс с сауной ФГБУ «МСГ» в отведенное администрацией ФГБУ «МСГ» время.",

#     "Проживающие в общежитии студенты обязаны ознакомиться с настоящими Правилами.",
#     "Проживающие в общежитии студенты обязаны cтрого соблюдать настоящие Правила, правила техники безопасности, правила пожарной безопасности, требования (рекомендации) Рсопотребнадзора.",
#     "Проживающие в общежитии студенты обязаны принимать участие в проведении инструкторско-методических занятий по теме: «Организация эвакуации людей из студенческого общежития при возникновении пожара и чрезвычайных ситуациях».",
#     "Проживающие в общежитии студенты обязаны при чрезвычайных ситуациях и срабатывании оповещения — покинуть общежитие.",
#     "Проживающие в общежитии студенты обязаны выполнять условия договора найма жилого помещения.",
#     "Проживающие в общежитии студенты обязаны В установленном порядке и сроки представлять документы для регистрации по месту пребывания, своевременно предоставлять в отдел учета, размещения и регистрации информацию о смене паспортных данных (20 лет — замена паспорта, смена фамилии и др. личные данные).",
#     "Проживающие в общежитии студенты обязаны ежегодно представлять администрации корпуса копию справки о прохождении флюорографии (ФЛГ).",
#     "Проживающие в общежитии студенты обязаны своевременно в соответствии с условиями договора найма жилого помещения в общежитии вносить плату в установленных размерах за проживание в общежитии и за все виды предоставляемых дополнительных платных услуг.",
#     "Проживающие в общежитии студенты обязаны по требованию администрации корпуса предъявлять электронный пропуск установленного образца на право входа в общежитие.",

#     "Проживающие в общежитии студенты обязаны обеспечить возможность осмотра жилой комнаты администрацией корпуса в присутствии членов Студенческого совета МСГ или проживающих на этаже студентов с целью контроля санитарного состояния, проверки сохранности имущества, проведения профилактических и других видов работ.",
#     "Проживающие в общежитии студенты обязаны не допускать, а в случае обнаружения сообщать администрации корпуса и администрации ФГБУ «МСГ», любые попытки распространения информации или пропаганды сомнительных организаций (террористических), так как это противоречит действующему законодательству РФ.",
#     "Проживающие в общежитии студенты обязаны принимать посетителей только в установленное администрацией ФГБУ «МСГ» время, согласно графику посещения гостей, утвержденному директором ФГБУ «МСГ». Время визитов для посторонних посетителей: среда с 17.00 до 21.00, суббота, воскресенье, праздничные дни с 13.00 до 21.00, время визитов для посетителей из ФГБУ «МСГ»: с понедельника по пятницу с 17.00 до 21.00, в субботу, воскресенье, праздничные дни с 13.00 до 21.00.",
#     "Проживающие в общежитии студенты обязаны при временном отсутствии более чем на 3 суток (каникулы, практика, стажировка и др.) письменно уведомить администрацию корпуса не менее чем за 2 (два) дня до предполагаемого выбытия.",
#     "Проживающие в общежитии студенты обязаныво время пользования помещениями для самостоятельных занятий и культурно-бытового назначения соблюдать тишину и не создавать препятствий другим проживающим в пользовании указанными помещениями.",
#     "Проживающие в общежитии студенты обязаныбережно относиться к помещениям, оборудованию и инвентарю.",
#     "Проживающие в общежитии студенты обязанынаходясь на кухне, проявлять повьшиенное внимание к работающим бытовым приборам (особенно к газовым плитам) во избежание задымления, возгорания (выключать кипящие чайники, кастрюли, подгорающую пищу и т.п.).",
#     "Проживающие в общежитии студенты обязанына основании графика, установленного Старостой этажа, добросовестно нести обязанности по дежурству на кухне.",

#     "Проживающие в общежитии студенты обязаныэкономно расходовать электроэнергию, газ и воду.",
#     "Проживающие в общежитии студенты обязанысоблюдать чистоту и порядок в жилых помещениях и местах общего пользования, осуществлять влажную уборку жилого помещения не реже 3-х раз в неделю, в соответствии с графиком уборки комнаты.",
#     "Проживающие в общежитии студенты обязаныв случае обнаружения неисправностей датчиков пожарной безопасности, электричества, отопительных батарей, инвентаря, оборудования и насекомых сообщить администрации корпуса либо заполнить форму заявки в системе АСУ «Заявки» по адресу: ВИр://арр.т1зе-зрь.га.",
#     "Проживающие в общежитии студенты обязанывозмещать причиненный материальный ущерб в соответствии с действующим законодательством и договором найма жилого помещения.",
#     "Проживающие в общежитии студенты обязанысоблюдать требования морально-этических норм поведения, поддерживать атмосферу доброжелательности и взаимного уважения по отношению к проживающим, работникам, администрации корпуса, администрации ФГБУ «МСГ» и членам Студенческого совета МСГ."
# ]

RAW_TEXTS_EN = [
    "Students living in the dormitory have the right to 24-hour access to their place of residence.",
    "Students living in the dormitory have the right to apply to the administration of the Federal State Budgetary Institution 'MSG' with an application, certified by the head of the dormitory, for the placement of relatives in the guest rooms of the dormitory (for a short period of stay, at least 2 days), parents - for any period (upon presentation of a document confirming the degree of kinship).",
    "Students living in the dormitory have the right to use the rooms for independent study and cultural and household premises, equipment, inventory of the dormitory.",
    "Students living in the dormitory have the right to contact the administration of the building with requests for timely repairs, replacement of equipment and inventory that failed through no fault of theirs.",
    "Students living in the dormitory have the right to move from one room to another in the same building, as well as to move from one building to another if there are vacancies, with the consent of the administration buildings.",
    "Students living in the dormitory have the right to participate in the formation and election of the MSG Student Council and to be elected to its composition.",
    "Students living in the dormitory have the right to participate (make proposals) through the MSG Student Council and the youth policy department of the FSBI 'MSG' in resolving issues of improving housing and living conditions, organizing educational work and leisure.",
    "Students living in the dormitory have the right to take part in social, sports and cultural and leisure events organized by the administration of the FSBI 'MSG' and the MSG Student Council.",
    "Students living in the dormitory have the right to use permitted household appliances in compliance with safety regulations and fire safety regulations.",
    "Students living in the dormitory have the right to visit the Interuniversity Educational and Sports Center free of charge at a time approved by the administration of the FSBI 'MSG' and agreed upon with the MSG Student Council."
]

AGENT_DRIVER_CONFIG = AgentDriverConfig(
    name='ollama',
    agent_config=AgentConnectorConfig(
        gen_strategy={"num_predict": 2048, "seed": 42, "top_k": 1, "temperature": 0.0},
        credentials={"host": 'localhost', "port": 11438},
        ext_params={"model": 'qwen2.5:7b', "timeout": 560, "keep_alive": -1}))

KV_CACHE_CONFIG = KeyValueDriverConfig(
    db_vendor='mixed_kv',
    db_config=KVDBConnectionConfig(
        need_to_clear=False,
        params={
            'mongo_config': KVDBConnectionConfig(
                host='localhost', port=27017,
                db_info={'db': 'memorize_db', 'table': None},
                params={'username': 'user', 'password': 'pass', 'max_storage': -1},
                need_to_clear=False),
            'redis_config': KVDBConnectionConfig(
                host='localhost', port=6379,
                db_info={'db': 0, 'table': None},
                params={'ss_name': 'sorted_node_pairs', 'hs_name': 'node_pairs', 'max_storage': 50000000},
                need_to_clear=False)}))

MEM_CONFIG1 = MemPipelineConfig(
    extractor_config=LLMExtractorConfig(
        lang='en', adriver_config=AGENT_DRIVER_CONFIG,
        triplets_extraction_task_config=AgentTripletExtrTaskConfigSelector.select(
            base_config_version='v1'),
        thesises_extraction_task_config=AgentThesisExtrTaskConfigSelector.select(
            base_config_version='v1')),
    updator_config=LLMUpdatorConfig(
        lang='en', adriver_config=AGENT_DRIVER_CONFIG,
        delete_obsolete_info=False))

MEM_CONFIG2 = MemPipelineConfig(
    extractor_config=LLMExtractorConfig(
        lang='en', adriver_config=AGENT_DRIVER_CONFIG,
        triplets_extraction_task_config=AgentTripletExtrTaskConfigSelector.select(
            base_config_version='v2'),
        thesises_extraction_task_config=AgentThesisExtrTaskConfigSelector.select(
            base_config_version='v2')),
    updator_config=LLMUpdatorConfig(
        lang='en', adriver_config=AGENT_DRIVER_CONFIG,
        delete_obsolete_info=False))
