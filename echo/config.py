# config.py

# ----- Таблица скидок ----- 
DISCOUNT_TABLE = [
    {'min-sum': 0,      'max-sum': 150000,  'discount': 1},
    {'min-sum': 150001, 'max-sum': 300000,  'discount': 2},
    {'min-sum': 300001, 'max-sum': 400000,  'discount': 3},
    {'min-sum': 400001, 'max-sum': 500000,  'discount': 4},
    {'min-sum': 500001, 'max-sum': 600000,  'discount': 5},
    {'min-sum': 600001, 'max-sum': 700000,  'discount': 6},
    {'min-sum': 700001, 'max-sum': 800000,  'discount': 7},
    {'min-sum': 800001, 'max-sum': 900000,  'discount': 8},
    {'min-sum': 900001, 'max-sum': 1000000, 'discount': 9},
]
 
# ----- Названия статусов -----
ST_N_GOOD                  = "Согласован"
ST_N_IN_WORK               = "В работе"
ST_N_SOG_ROP               = "На согласование РОП"
ST_N_SOG_FINDIR            = "На согласование Фин.директор"
ST_N_SOG_MANAGER           = "На согласование Менеджер"
ST_N_SOG_TECHNOLOG         = "На согласование Технолог"
ST_N_PRC_FINDIR            = "Цены Фин.директор"
ST_N_PRC_TECHNOLOG         = "Цены Технолог"

# ----- Названия галочек -----
G_N_ROP        = "Счёт согласован. РОП"
G_N_FINDIR     = "Счёт согласован. Финдиректор"
G_N_MANAGER    = "Счёт согласован. Менеджер"
G_N_TECHNOLOG  = "Счёт согласован. Технолог"

# ----- ID галочек (атрибутов) -----
ATTR_ID = {
    G_N_ROP:       "80074015-b230-11ef-0a80-0981000eb659",
    G_N_FINDIR:    "72a511bc-d4b4-11ef-0a80-07250008bd6e",
    G_N_MANAGER:   "e5461d4e-d340-11ef-0a80-0886000f639b",
    G_N_TECHNOLOG: "800741de-b230-11ef-0a80-0981000eb65a"
}
