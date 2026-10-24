from __future__ import annotations

from dataclasses import dataclass


DIMENSIONS = (
    "dominance",
    "care",
    "dependence",
    "empathy",
    "romance",
    "playfulness",
    "stability",
    "maturity",
)

DIMENSION_LABELS = {
    "dominance": "主导",
    "care": "照顾",
    "dependence": "依赖",
    "empathy": "共情",
    "romance": "浪漫",
    "playfulness": "玩乐",
    "stability": "稳定",
    "maturity": "成熟",
}


def dimension_label(key: str) -> str:
    return DIMENSION_LABELS.get(key, key)


RELATION_TYPES: dict[str, dict[str, str]] = {
    "bestie": {
        "name": "死党型",
        "subtitle": "能一起闹，也能一起稳下来",
        "role_a": "带节奏的人",
        "role_b": "接住节奏的人",
        "highlight": "你们很容易在同一件小事上笑成一团。",
        "advice": "保持坦诚，把轻松和认真都留给彼此。",
    },
    "siblings": {
        "name": "兄弟/姐妹型",
        "subtitle": "像家人一样吵闹，也像家人一样照顾",
        "role_a": "嘴硬心软的人",
        "role_b": "默默兜底的人",
        "highlight": "相处里有熟悉的安全感。",
        "advice": "把习惯性的忽略，说成明确的感谢。",
    },
    "childhood_friend": {
        "name": "青梅竹马型",
        "subtitle": "很多默契都不用解释",
        "role_a": "记得细节的人",
        "role_b": "保持连接的人",
        "highlight": "你们对彼此的成长轨迹都很熟。",
        "advice": "偶尔把旧回忆翻出来，也要给新变化留位置。",
    },
    "confidant": {
        "name": "知己型",
        "subtitle": "能懂你安静下来的那一面",
        "role_a": "倾听的人",
        "role_b": "表达的人",
        "highlight": "适合放下防备，认真说心里话。",
        "advice": "继续保留这种不打扰的理解。",
    },
    "teacher_student": {
        "name": "师生型",
        "subtitle": "一个指路，一个吸收，关系里有引导感",
        "role_a": "引导者",
        "role_b": "学习者",
        "highlight": "你们很适合在交流里彼此成长。",
        "advice": "把建议说得具体一点，会更好接住。",
    },
    "twin": {
        "name": "双胞胎型",
        "subtitle": "像镜子，也像同频",
        "role_a": "同频的一边",
        "role_b": "另一边同频的人",
        "highlight": "你们的反应常常快得像同步。",
        "advice": "保留一点差异，会让关系更有层次。",
    },
    "frienemy": {
        "name": "欢喜冤家型",
        "subtitle": "会拌嘴，但总能把话接回温暖里",
        "role_a": "挑起话题的人",
        "role_b": "接招的人",
        "highlight": "你们的互动自带一点火花。",
        "advice": "玩笑要留分寸，认真时也别互相躲开。",
    },
    "companion": {
        "name": "陪伴型",
        "subtitle": "不一定总热闹，但一直都在",
        "role_a": "陪着走的人",
        "role_b": "一起慢下来的人",
        "highlight": "彼此都能在普通日子里提供安稳。",
        "advice": "把陪伴说出口，比默默做完更有力。",
    },
    "complementary": {
        "name": "互补型",
        "subtitle": "一个补短板，一个补节奏",
        "role_a": "补节奏的人",
        "role_b": "补短板的人",
        "highlight": "你们在不同的位置上都很有用。",
        "advice": "别把互补理解成理所当然。",
    },
    "mirror": {
        "name": "镜像型",
        "subtitle": "会看见对方身上自己的影子",
        "role_a": "照见自己的人",
        "role_b": "被照见的人",
        "highlight": "相似之处让你们很容易理解彼此。",
        "advice": "也要认真看见彼此的不同。",
    },
    "contrast": {
        "name": "反差型",
        "subtitle": "差异很明显，但组合在一起很顺眼",
        "role_a": "强势的一边",
        "role_b": "柔和的一边",
        "highlight": "不同的节奏反而让关系更立体。",
        "advice": "别把差异变成误会。",
    },
    "healing": {
        "name": "治愈型",
        "subtitle": "和你在一起，总会慢慢安静下来",
        "role_a": "安抚者",
        "role_b": "被安抚者",
        "highlight": "你们很容易给彼此情绪缓冲。",
        "advice": "把柔软保留下来，也把边界说清。",
    },
    "growing": {
        "name": "成长型",
        "subtitle": "在对方身上，都会看见自己变好的方向",
        "role_a": "推动成长的人",
        "role_b": "接住成长的人",
        "highlight": "你们适合一起往前走。",
        "advice": "别只盯结果，也要看见过程。",
    },
    "adventure": {
        "name": "冒险型",
        "subtitle": "很容易一起把日子过成小探险",
        "role_a": "开路的人",
        "role_b": "跟上的人",
        "highlight": "你们的关系里有行动力。",
        "advice": "开心要分享，风险也要商量。",
    },
    "harbor": {
        "name": "港湾型",
        "subtitle": "累了的时候，总能回到彼此身边",
        "role_a": "靠岸的人",
        "role_b": "守岸的人",
        "highlight": "稳定和照顾感都很强。",
        "advice": "把依赖说得温柔一点，把回应做得稳定一点。",
    },
    "parent_child": {
        "name": "亲子型",
        "subtitle": "一边照顾，一边被牵挂",
        "role_a": "照看者",
        "role_b": "被照看者",
        "highlight": "你们很容易产生照顾与被照顾的互动。",
        "advice": "把照顾做成尊重，不做成控制。",
    },
}


@dataclass(frozen=True, slots=True)
class QuestionSeed:
    question_text: str
    question_type: str
    scene_tag: str
    option_texts: tuple[str, ...]
    option_payloads: tuple[dict[str, int], ...]


def _question(
    question_text: str,
    question_type: str,
    scene_tag: str,
    options: tuple[tuple[str, dict[str, int]], ...],
) -> QuestionSeed:
    return QuestionSeed(
        question_text=question_text,
        question_type=question_type,
        scene_tag=scene_tag,
        option_texts=tuple(option_text for option_text, _ in options),
        option_payloads=tuple(payload for _, payload in options),
    )


_SCALE_LEVELS = (
    ("完全符合", 3),
    ("比较符合", 2),
    ("不太符合", 1),
    ("完全不符合", 0),
)


def _scale(question_text: str, scene_tag: str, dimension: str) -> QuestionSeed:
    options = tuple(
        (text, {dimension: weight} if weight else {})
        for text, weight in _SCALE_LEVELS
    )
    return _question(question_text, "scale", scene_tag, options)


# Docs/18 §5 定稿题库：40 题，每维 5 题（3 单选 + 1 二选一 + 1 量表/多选）。
# 权重遵循 Docs/18 §4：情景题选项主投单维度 +3；量表题四档 +3/+2/+1/+0。
CURRENT_TEST_SEEDS: tuple[QuestionSeed, ...] = (
    # ── 主导 dominance（Q1–Q5）──
    _question(
        "你们约好聚餐，到店发现门口排长队。你更倾向——",
        "single_choice",
        "聚餐排队",
        (
            ("直接提议换一家不用排的", {"dominance": 3}),
            ("问大家愿不愿意等，再一起决定", {"maturity": 3}),
            ("都行，听大家安排", {"dependence": 3}),
            ("先安抚「不急，边等边聊也不错」", {"care": 3}),
        ),
    ),
    _question(
        "几个人商量周末去哪玩，聊了半天定不下来。你更可能——",
        "single_choice",
        "周末去哪",
        (
            ("拍个方案说「就去这里吧」", {"dominance": 3}),
            ("把大家的想法整理成两三个选项让大家选", {"maturity": 3}),
            ("看谁最想去哪，就跟着去", {"dependence": 3}),
            ("观察谁比较累，先照顾大家的体力", {"care": 3}),
        ),
    ),
    _question(
        "一起做决定时，你最常扮演的角色是——",
        "single_choice",
        "做决定",
        (
            ("提出方向、推进落地的人", {"dominance": 3}),
            ("会先问清每个人想法的人", {"empathy": 3}),
            ("跟随大多数、让事情稳一点的人", {"stability": 3}),
            ("提醒大家注意细节和风险的人", {"maturity": 3}),
        ),
    ),
    _question(
        "碰到意见不一致，你更倾向——",
        "either_or",
        "分歧",
        (
            ("尽快拍板，先动起来再说", {"dominance": 3}),
            ("多聊几轮，等大家都有底再定", {"stability": 3}),
        ),
    ),
    _scale("「一群人不知道怎么办的时候，你常常会主动站出来拿主意。」", "拿主意", "dominance"),
    # ── 照顾 care（Q6–Q10）──
    _question(
        "朋友生病了给你发消息。你的第一反应更接近——",
        "single_choice",
        "朋友生病",
        (
            ("立刻问情况，能帮忙就帮", {"care": 3}),
            ("认真听对方说，先让他说完", {"empathy": 3}),
            ("有点不知所措，等他开口提要求", {"dependence": 3}),
            ("给一些实用建议，怎么更快好起来", {"maturity": 3}),
        ),
    ),
    _question(
        "一起吃饭，有人明显心情不好、话很少。你更可能——",
        "single_choice",
        "有人低落",
        (
            ("主动给他夹菜、找话照顾他", {"care": 3}),
            ("私下问他「是不是有事，想聊聊吗」", {"empathy": 3}),
            ("安静陪着，不主动打扰", {"stability": 3}),
            ("讲点轻松的事，把气氛带起来", {"playfulness": 3}),
        ),
    ),
    _question(
        "旅行途中同伴明显累了。你更倾向——",
        "single_choice",
        "同伴累了",
        (
            ("放慢节奏，迁就对方", {"care": 3}),
            ("提议先休息，顺便规划下段路", {"dominance": 3}),
            ("看对方怎么想，跟着调整", {"dependence": 3}),
            ("找个地方坐坐，聊点开心的", {"playfulness": 3}),
        ),
    ),
    _question(
        "你更享受的关系状态是——",
        "either_or",
        "关系状态",
        (
            ("被需要、能照顾到对方", {"care": 3}),
            ("被照顾、有人替你兜底", {"dependence": 3}),
        ),
    ),
    _question(
        "朋友遇到麻烦时，你通常会做哪些事？（可多选）",
        "multi_select",
        "朋友遇麻烦",
        (
            ("主动提出帮他分担", {"care": 3}),
            ("陪他聊聊，让他说痛快", {"empathy": 3}),
            ("一起想办法解决", {"maturity": 3}),
            ("带他去放松一下", {"playfulness": 3}),
        ),
    ),
    # ── 依赖 dependence（Q11–Q15）──
    _question(
        "你心情不好的时候，更希望对方——",
        "single_choice",
        "心情不好",
        (
            ("主动来关心我、陪着我", {"dependence": 3}),
            ("给我空间，我自己缓缓", {"maturity": 3}),
            ("先哄我，再帮我分析", {"care": 3}),
            ("讲点好笑的事转移注意力", {"playfulness": 3}),
        ),
    ),
    _question(
        "一个人做重要决定时，你更倾向——",
        "single_choice",
        "重要决定",
        (
            ("很想找个人商量，听听意见", {"dependence": 3}),
            ("自己拿主意，定完再告诉别人", {"dominance": 3}),
            ("会反复想，怕自己考虑不周", {"stability": 3}),
            ("先列出利弊，理性判断", {"maturity": 3}),
        ),
    ),
    _question(
        "对方很久没回你消息，你更可能——",
        "single_choice",
        "没回消息",
        (
            ("有点不安，会再发一条问问", {"dependence": 3}),
            ("理解对方可能有事，继续忙自己的", {"maturity": 3}),
            ("告诉自己别多想，等他回", {"stability": 3}),
            ("主动打个电话，直接确认", {"dominance": 3}),
        ),
    ),
    _question(
        "你更需要的关系状态是——",
        "either_or",
        "需要",
        (
            ("有人时时回应、陪我一起", {"dependence": 3}),
            ("各自独立，需要时再靠近", {"maturity": 3}),
        ),
    ),
    _scale("「对方长时间没有回应，你会比较焦虑。」", "回应焦虑", "dependence"),
    # ── 共情 empathy（Q16–Q20）──
    _question(
        "朋友跟你说他最近压力很大。你更可能——",
        "single_choice",
        "朋友压力大",
        (
            ("先认真听，理解他的情绪", {"empathy": 3}),
            ("直接给建议，怎么解决压力", {"maturity": 3}),
            ("约他出来散心放松", {"playfulness": 3}),
            ("说「我也有过类似经历」，让他不孤单", {"care": 3}),
        ),
    ),
    _question(
        "对方突然情绪低落，但没说原因。你更倾向——",
        "single_choice",
        "情绪低落",
        (
            ("耐心陪着他，等他想说再说", {"empathy": 3}),
            ("追问到底怎么了", {"dominance": 3}),
            ("做点让他开心的事", {"playfulness": 3}),
            ("给他空间，先不打扰", {"stability": 3}),
        ),
    ),
    _question(
        "和别人意见不同时，你更可能——",
        "single_choice",
        "意见不同",
        (
            ("先理解他为什么这么想", {"empathy": 3}),
            ("摆事实讲道理说服他", {"maturity": 3}),
            ("不争了，听对方的", {"dependence": 3}),
            ("各退一步找中间方案", {"stability": 3}),
        ),
    ),
    _question(
        "你更擅长——",
        "either_or",
        "擅长",
        (
            ("感受到对方没说的情绪", {"empathy": 3}),
            ("把复杂的事讲清楚、解决掉", {"maturity": 3}),
        ),
    ),
    _question(
        "你觉得自己比较擅长——（可多选）",
        "multi_select",
        "共情表现",
        (
            ("察觉到对方没说的情绪", {"empathy": 3}),
            ("站在对方角度想问题", {"empathy": 3}),
            ("把矛盾谈开、不让情绪发酵", {"maturity": 3}),
            ("用行动照顾对方的情绪", {"care": 3}),
        ),
    ),
    # ── 浪漫 romance（Q21–Q25）──
    _question(
        "重要的纪念日或节日，你更倾向——",
        "single_choice",
        "纪念日",
        (
            ("认真准备惊喜和仪式感", {"romance": 3}),
            ("一起吃顿饭，简单就好", {"stability": 3}),
            ("看对方怎么安排，都开心", {"dependence": 3}),
            ("安排一场有意思的活动", {"playfulness": 3}),
        ),
    ),
    _question(
        "表达喜欢或在意时，你更习惯——",
        "single_choice",
        "表达喜欢",
        (
            ("直接说出来，也喜欢被直接表达", {"romance": 3}),
            ("用行动照顾对方来表达", {"care": 3}),
            ("藏在心里，不好意思说", {"dependence": 3}),
            ("用开玩笑的方式带过去", {"playfulness": 3}),
        ),
    ),
    _question(
        "你理想中两个人相处，更像——",
        "single_choice",
        "理想相处",
        (
            ("有说不完的话，常常被对方打动", {"romance": 3}),
            ("踏实安稳，彼此靠得住", {"stability": 3}),
            ("一起闹一起玩，热闹开心", {"playfulness": 3}),
            ("互相理解，精神上有默契", {"empathy": 3}),
        ),
    ),
    _question(
        "你更看重——",
        "either_or",
        "看重",
        (
            ("节日里的小惊喜和仪式感", {"romance": 3}),
            ("日常里稳定的陪伴", {"stability": 3}),
        ),
    ),
    _scale("「你会为重要的人花心思准备小惊喜。」", "准备惊喜", "romance"),
    # ── 玩乐 playfulness（Q26–Q30）──
    _question(
        "一群朋友聚会，你通常——",
        "single_choice",
        "聚会角色",
        (
            ("负责活跃气氛、抛梗", {"playfulness": 3}),
            ("照顾每个人，让大家舒服", {"care": 3}),
            ("安静听着，跟着笑", {"stability": 3}),
            ("聊点深入的，把话题往心里带", {"empathy": 3}),
        ),
    ),
    _question(
        "对方心情低落，你更倾向——",
        "single_choice",
        "哄低落",
        (
            ("讲段子、逗他开心", {"playfulness": 3}),
            ("陪他安静待着，听他倾诉", {"empathy": 3}),
            ("带他去做点新鲜有趣的事", {"playfulness": 3}),
            ("帮他分析问题出在哪", {"maturity": 3}),
        ),
    ),
    _question(
        "周末没有安排，你更想——",
        "single_choice",
        "周末没安排",
        (
            ("约人一起玩、找点乐子", {"playfulness": 3}),
            ("宅着休息，安静充电", {"stability": 3}),
            ("看朋友想干嘛就干嘛", {"dependence": 3}),
            ("把积压的事处理掉", {"maturity": 3}),
        ),
    ),
    _question(
        "相处中你更看重——",
        "either_or",
        "看重",
        (
            ("一起开心、常有笑声", {"playfulness": 3}),
            ("安稳踏实、细水长流", {"stability": 3}),
        ),
    ),
    _question(
        "你喜欢的关系相处方式包括——（可多选）",
        "multi_select",
        "相处方式",
        (
            ("一起尝试新鲜好玩的事", {"playfulness": 3}),
            ("常常开玩笑互怼", {"playfulness": 3}),
            ("一起安静待着也不尴尬", {"stability": 3}),
            ("常常深入聊心里话", {"empathy": 3}),
        ),
    ),
    # ── 稳定 stability（Q31–Q35）──
    _question(
        "一段关系里，你最看重——",
        "single_choice",
        "最看重",
        (
            ("稳定、可预期、靠得住", {"stability": 3}),
            ("新鲜感、常有惊喜", {"romance": 3}),
            ("被理解和回应", {"empathy": 3}),
            ("一起成长、共同进步", {"maturity": 3}),
        ),
    ),
    _question(
        "面对计划外的变化，你更倾向——",
        "single_choice",
        "面对变化",
        (
            ("喜欢按计划来，变动会让我不安", {"stability": 3}),
            ("拥抱变化，觉得新鲜", {"playfulness": 3}),
            ("看情况，跟着大家走", {"dependence": 3}),
            ("主动调整，把变化安排好", {"dominance": 3}),
        ),
    ),
    _question(
        "你更认同——",
        "single_choice",
        "关系靠什么",
        (
            ("关系靠日积月累的踏实", {"stability": 3}),
            ("关系靠心动的瞬间", {"romance": 3}),
            ("关系靠一起经历的精彩", {"playfulness": 3}),
            ("关系靠深入的懂得", {"empathy": 3}),
        ),
    ),
    _question(
        "你更怕——",
        "either_or",
        "更怕",
        (
            ("关系突然变淡、失去联系", {"stability": 3}),
            ("日子太重复、没有新鲜感", {"playfulness": 3}),
        ),
    ),
    _scale("「你喜欢稳定、有规律、可预期的相处节奏。」", "稳定节奏", "stability"),
    # ── 成熟 maturity（Q36–Q40）──
    _question(
        "和亲近的人发生矛盾时，你更可能——",
        "single_choice",
        "矛盾",
        (
            ("冷静沟通，把话说清楚", {"maturity": 3}),
            ("先哄对方，情绪缓下来再说", {"care": 3}),
            ("冷战，等对方先低头", {"dependence": 3}),
            ("用玩笑把矛盾带过去", {"playfulness": 3}),
        ),
    ),
    _question(
        "对方做了让你不舒服的事，你更倾向——",
        "single_choice",
        "被冒犯",
        (
            ("直接但温和地说出自己的感受", {"maturity": 3}),
            ("忍着不说，怕影响关系", {"dependence": 3}),
            ("用行动暗示，希望对方自己发现", {"empathy": 3}),
            ("找朋友吐槽，先发泄一下", {"playfulness": 3}),
        ),
    ),
    _question(
        "关于「边界」，你更认同——",
        "single_choice",
        "关于边界",
        (
            ("关系里要有清晰的边界，彼此尊重", {"maturity": 3}),
            ("关系好就该不分你我", {"care": 3}),
            ("边界感别太强，不然显得生分", {"dependence": 3}),
            ("顺其自然，不刻意划分", {"stability": 3}),
        ),
    ),
    _question(
        "遇到分歧时，你更倾向——",
        "either_or",
        "分歧",
        (
            ("坐下来把道理和感受都讲清楚", {"maturity": 3}),
            ("先让一步，维持和睦最重要", {"care": 3}),
        ),
    ),
    _question(
        "和亲近的人产生分歧时，你通常会——（可多选）",
        "multi_select",
        "处理分歧",
        (
            ("冷静地把想法说清楚", {"maturity": 3}),
            ("尊重对方的边界，不越界", {"maturity": 3}),
            ("先安抚情绪再谈问题", {"care": 3}),
            ("找点轻松的缓冲，不硬碰", {"playfulness": 3}),
        ),
    ),
)


def build_current_test_seed() -> tuple[QuestionSeed, ...]:
    return CURRENT_TEST_SEEDS


def build_dimension_max_raw_scores(seeds: tuple[QuestionSeed, ...] = CURRENT_TEST_SEEDS) -> dict[str, int]:
    """每维可得原始分上限：多选题可全选按选项求和，其余题型取最大选项权重。"""
    max_scores = {dimension: 0 for dimension in DIMENSIONS}
    for seed in seeds:
        for dimension in DIMENSIONS:
            if seed.question_type == "multi_select":
                contribution = sum(payload.get(dimension, 0) for payload in seed.option_payloads)
            else:
                contribution = max(payload.get(dimension, 0) for payload in seed.option_payloads)
            max_scores[dimension] += contribution
    return max_scores


def build_user_short_summary(dimension_scores: dict[str, int]) -> str:
    ordered = sorted(dimension_scores.items(), key=lambda item: (-item[1], item[0]))
    top = ordered[:2]
    if not top:
        return "你是一个风格稳定、表达清楚的参与者。"
    if len(top) == 1:
        return f"你更像一个{dimension_label(top[0][0])}很突出的参与者。"
    return f"你更像一个{dimension_label(top[0][0])}、{dimension_label(top[1][0])}都比较突出的参与者。"
