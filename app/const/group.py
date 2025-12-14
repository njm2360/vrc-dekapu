from zoneinfo import ZoneInfo


DEKAPU_WORLD_ID = "wrld_1af53798-92a3-4c3f-99ae-a7c42ec6084d"

DKPSKL_GROUP_ID = "grp_f664b62c-df1a-4ad4-a1df-2b9df679bc04"
SKILL_GROUP_ID = "grp_746f4574-b608-41d3-baed-03fa906391d5"

BUPPA_RENGO_ROLE_ID = "grol_c8676ba2-83e7-4780-9cb9-fbe9f60c25ba"


INSTANCE_NAME_LIST = [
    "リンゴ支部",
    "イチゴ支部",
    "メロン支部",
    "スイカ支部",
    "バナナ支部",
    "ブドウ支部",
    "マンゴー支部",
    "レモン支部",
]

GROUPNAME_MAP = {
    "ブッパ連合": DKPSKL_GROUP_ID,
    "ブッパ会": SKILL_GROUP_ID,
}

TZ = ZoneInfo("Asia/Tokyo")
