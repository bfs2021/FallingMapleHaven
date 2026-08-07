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


SCENE_TEXTS = (
    "临时改计划",
    "群聊突然冷场",
    "对方情绪低落",
    "一起等车的时候",
    "需要做一个决定",
    "节日送礼物的时候",
    "遇到小摩擦时",
    "周末不知道做什么",
)


@dataclass(frozen=True, slots=True)
class QuestionSeed:
    question_text: str
    scene_tag: str
    option_texts: tuple[str, ...]
    option_payloads: tuple[dict[str, int], ...]


def _option_payload(question_index: int, option_index: int) -> dict[str, int]:
    payload = {dimension: 0 for dimension in DIMENSIONS}
    main = DIMENSIONS[(question_index + option_index) % len(DIMENSIONS)]
    secondary = DIMENSIONS[(question_index * 3 + option_index + 1) % len(DIMENSIONS)]
    payload[main] = 3 if option_index == 0 else 2
    if secondary != main:
        payload[secondary] = 1
    return payload


def build_current_test_seed() -> tuple[QuestionSeed, ...]:
    questions: list[QuestionSeed] = []
    for question_index in range(40):
        scene = SCENE_TEXTS[question_index % len(SCENE_TEXTS)]
        option_count = 2 + (question_index % 3)
        option_texts = tuple(
            f"选项 {question_index + 1}-{chr(65 + option_index)}"
            for option_index in range(option_count)
        )
        option_payloads = tuple(
            _option_payload(question_index, option_index)
            for option_index in range(option_count)
        )
        questions.append(
            QuestionSeed(
                question_text=f"第 {question_index + 1} 题：面对{scene}，你更像哪一种反应？",
                scene_tag=scene,
                option_texts=option_texts,
                option_payloads=option_payloads,
            )
        )
    return tuple(questions)


def build_user_short_summary(dimension_scores: dict[str, int]) -> str:
    ordered = sorted(dimension_scores.items(), key=lambda item: (-item[1], item[0]))
    top = ordered[:2]
    if not top:
        return "你是一个风格稳定、表达清楚的参与者。"
    if len(top) == 1:
        return f"你更像一个{top[0][0]}感很强的参与者。"
    return f"你更像一个{top[0][0]}、{top[1][0]}都比较突出的参与者。"
