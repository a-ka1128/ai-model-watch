export type GlossaryTerm = { id: string; name: string; aliases: string[]; explanation: string; source?: string };

// Curated explanations are separate from the article author's claims.
export const glossary: GlossaryTerm[] = [
  { id: "nonogram", name: "논오그램 퍼즐", aliases: ["논오그램 퍼즐", "논오그램", "노노그램", "nonogram", "nonograms", "picross"], explanation: "가로·세로 줄에 적힌 숫자를 단서로 격자의 칸을 칠해 그림을 완성하는 논리 퍼즐입니다. 예를 들어 ‘3 1’은 세 칸을 연속으로 칠하고, 한 칸 이상 비운 뒤 한 칸을 칠하라는 뜻입니다.", source: "https://logicpuzzles.games/nonogram/how-to-play/" },
  { id: "llm", name: "LLM · 대규모 언어 모델", aliases: ["LLMs", "LLM", "대규모 언어 모델", "대형 언어 모델"], explanation: "많은 텍스트를 학습해 질문에 답하거나 글·코드를 생성하는 AI 모델입니다. ChatGPT나 Claude 같은 서비스의 핵심 기술입니다.", source: "https://huggingface.co/docs/transformers/main/glossary" },
  { id: "open-weights", name: "오픈 웨이트", aliases: ["오픈 웨이트", "오픈웨이트", "오픈 가중치", "open-weight", "open weights", "open-weights"], explanation: "학습이 끝난 AI 모델의 가중치 파일을 공개해 내려받을 수 있는 형태입니다. 가중치는 모델이 학습한 숫자 값입니다. 학습 데이터나 코드까지 전부 공개됐다는 뜻은 아니며, 사용 조건은 모델마다 다릅니다.", source: "https://opensource.org/ai/open-weights" },
  { id: "benchmark", name: "벤치마크", aliases: ["벤치마크", "benchmark", "benchmarks"], explanation: "여러 모델을 같은 문제와 조건으로 시험해 성능을 비교하는 평가입니다. 한 평가의 점수가 실제 모든 작업에서의 성능을 뜻하지는 않습니다.", source: "https://huggingface.co/docs/leaderboards/index" },
  { id: "inference", name: "추론", aliases: ["추론", "inference"], explanation: "AI 글에서는 문맥에 따라 두 뜻으로 쓰입니다. 모델을 실행해 답을 만드는 과정, 또는 문제를 단계적으로 생각해 해결하는 능력을 가리킵니다." },
  { id: "tokens", name: "토큰", aliases: ["토큰", "tokens", "token"], explanation: "AI가 글을 처리할 때 사용하는 작은 텍스트 단위입니다. 한 단어가 여러 토큰으로 나뉠 수 있어, 토큰 수와 글자 수는 같지 않습니다.", source: "https://huggingface.co/docs/transformers/main/glossary" },
  { id: "context", name: "컨텍스트 윈도", aliases: ["컨텍스트 윈도우", "컨텍스트 윈도", "context window", "문맥 창"], explanation: "모델이 한 번에 참고할 수 있는 대화와 문서의 최대 분량입니다. 보통 토큰 수로 표시하며, 질문과 답변에 필요한 분량을 함께 고려해야 합니다." },
  { id: "fine-tuning", name: "파인튜닝", aliases: ["파인튜닝", "미세 조정", "fine-tuning", "finetuning"], explanation: "이미 학습된 모델을 추가 데이터로 더 학습시켜 특정 작업이나 말투에 맞추는 과정입니다.", source: "https://huggingface.co/docs/transformers/main/training" },
  { id: "quantization", name: "양자화", aliases: ["양자화", "quantization"], explanation: "모델의 숫자 값을 더 적은 비트로 표현해 메모리 사용량을 줄이는 방법입니다. 실행 환경과 방식에 따라 속도나 답변 품질이 달라질 수 있습니다.", source: "https://huggingface.co/docs/transformers/main/quantization/overview" },
  { id: "multimodal", name: "멀티모달", aliases: ["멀티모달", "multimodal"], explanation: "텍스트뿐 아니라 이미지·음성·영상 등 여러 종류의 정보를 함께 처리하는 기능을 뜻합니다." },
  { id: "rag", name: "RAG · 검색 증강 생성", aliases: ["검색 증강 생성", "RAG"], explanation: "질문과 관련된 문서를 먼저 찾고, 그 내용을 모델에 제공해 답변을 만드는 방식입니다. 검색한 자료의 정확성도 답변 품질에 영향을 줍니다.", source: "https://huggingface.co/docs/transformers/main/model_doc/rag" },
  { id: "hallucination", name: "환각", aliases: ["할루시네이션", "환각", "hallucination"], explanation: "AI가 사실이 아니거나 근거가 없는 내용을 그럴듯하게 만들어 내는 현상입니다." },
  { id: "api", name: "API", aliases: ["API"], explanation: "다른 프로그램의 기능을 정해진 방식으로 요청하고 결과를 받는 연결 방법입니다. 예를 들어 앱이 AI 서버에 질문을 보내 답변을 받는 데 사용합니다." },
  { id: "gpu", name: "GPU", aliases: ["GPU", "GPUs"], explanation: "많은 계산을 동시에 처리하는 장치입니다. 그래픽 처리뿐 아니라 AI 모델의 학습과 실행에도 사용합니다." },
  { id: "vram", name: "VRAM", aliases: ["VRAM", "비디오 메모리"], explanation: "그래픽 카드에 있는 메모리입니다. AI 모델을 실행할 때 모델 파일과 계산 중간 결과를 담는 공간으로 사용합니다." },
  { id: "parameters", name: "파라미터", aliases: ["파라미터", "parameters"], explanation: "모델이 학습 과정에서 조정하는 숫자 값입니다. ‘8B’ 모델은 보통 약 80억 개의 파라미터가 있다는 뜻이며, 개수가 많다고 항상 더 좋은 답을 만드는 것은 아닙니다." },
  { id: "latency", name: "지연 시간", aliases: ["레이턴시", "latency"], explanation: "요청을 보낸 뒤 응답을 받기까지 기다리는 시간입니다. AI에서는 첫 글자가 나오기까지의 시간과 전체 답변이 끝나는 시간을 구분하기도 합니다." },
  { id: "false-positive", name: "거짓 양성 · 오탐", aliases: ["거짓 긍정", "거짓 양성", "false positive", "false positives"], explanation: "문제가 없는 대상을 문제가 있다고 잘못 판단한 경우입니다. 예를 들어 정상적인 질문을 위험한 질문으로 분류해 차단하는 상황입니다." },
];

const aliases = glossary.flatMap(term => term.aliases.map(alias => ({ alias, term }))).sort((a, b) => b.alias.length - a.alias.length);
const escapeRegex = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const pattern = aliases.map(({ alias }) => /^[a-z]/i.test(alias) ? `(?<![a-z0-9])${escapeRegex(alias)}(?![a-z0-9])` : escapeRegex(alias)).join("|");
export type TextPart = { text: string; term?: GlossaryTerm };

export function annotate(text: string): TextPart[] {
  const parts: TextPart[] = [];
  const expression = new RegExp(`https?:\\/\\/[^\\s]+|${pattern}`, "gi");
  let end = 0;
  for (const match of Array.from(text.matchAll(expression))) {
    const index = match.index!;
    if (index > end) parts.push({ text: text.slice(end, index) });
    const term = aliases.find(item => item.alias.toLowerCase() === match[0].toLowerCase())?.term;
    parts.push({ text: match[0], term });
    end = index + match[0].length;
  }
  if (end < text.length) parts.push({ text: text.slice(end) });
  return parts;
}

export function termsIn(text: string): GlossaryTerm[] {
  const seen = new Set<string>();
  return annotate(text).flatMap(part => {
    if (!part.term || seen.has(part.term.id)) return [];
    seen.add(part.term.id);
    return [part.term];
  });
}
