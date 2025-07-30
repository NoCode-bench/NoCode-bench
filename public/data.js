var _verified = [
  { method: "Agentless", model: 'Qwen3-235B', score: 9.65, org: 'https://brand.illinois.edu/wp-content/uploads/2024/02/Color-Variation-Orange-Block-I-White-Background.png', site: '', date: '2025-07-01' },
  { method: "Agentless", model: 'DeepSeek-R1', score: 11.40, org: 'https://brand.illinois.edu/wp-content/uploads/2024/02/Color-Variation-Orange-Block-I-White-Background.png', site: '', date: '2025-07-01' },
  { method: "Agentless", model: 'DeepSeek-v3', score: 14.91, org: 'https://brand.illinois.edu/wp-content/uploads/2024/02/Color-Variation-Orange-Block-I-White-Background.png', site: '', date: '2025-07-01' },
  { method: "Agentless", model: 'GPT-4o', score: 7.89, org: 'https://brand.illinois.edu/wp-content/uploads/2024/02/Color-Variation-Orange-Block-I-White-Background.png', site: '', date: '2025-07-01' },
  { method: "Agentless ", model: 'Gemini-2.5-Pro', score: 8.77, org: 'https://brand.illinois.edu/wp-content/uploads/2024/02/Color-Variation-Orange-Block-I-White-Background.png', site: '', date: '2025-07-01' },
  { method: "Agentless ", model: 'Claude-4-Sonnet', score: 15.79, org: 'https://brand.illinois.edu/wp-content/uploads/2024/02/Color-Variation-Orange-Block-I-White-Background.png', site: '', date: '2025-07-01' },
  { method: "OpenHands", model: 'Qwen3-235B', score: 5.26, org: 'https://avatars.githubusercontent.com/u/166046056?s=200&v=4', site: '', date: '2025-07-01' },
  { method: "OpenHands", model: 'DeepSeek-R1', score: 3.51, org: 'https://avatars.githubusercontent.com/u/166046056?s=200&v=4', site: '', date: '2025-07-01' },
  { method: "OpenHands", model: 'DeepSeek-v3', score: 7.02, org: 'https://avatars.githubusercontent.com/u/166046056?s=200&v=4', site: '', date: '2025-07-01' },
  { method: "OpenHands", model: 'GPT-4o', score: 2.63, org: 'https://avatars.githubusercontent.com/u/166046056?s=200&v=4', site: '', date: '2025-07-01' },
  { method: "OpenHands", model: 'Gemini-2.5-Pro', score: 0.00, org: 'https://avatars.githubusercontent.com/u/166046056?s=200&v=4', site: '', date: '2025-07-01' },
  { method: "OpenHands", model: 'Claude-4-Sonnet', score: 15.79, org: 'https://avatars.githubusercontent.com/u/166046056?s=200&v=4', site: '', date: '2025-07-01' },
]
var _full = [
  { method: "Agentless ", model: 'Claude-4-Sonnet', score: 3.94, org: 'https://brand.illinois.edu/wp-content/uploads/2024/02/Color-Variation-Orange-Block-I-White-Background.png', site: '', date: '2025-07-01' },
  { method: "Agentless", model: 'DeepSeek-v3', score: 6.15, org: 'https://brand.illinois.edu/wp-content/uploads/2024/02/Color-Variation-Orange-Block-I-White-Background.png', site: '', date: '2025-07-01' },
  { method: "Agentless", model: 'GPT-4o', score: 6.94, org: 'https://brand.illinois.edu/wp-content/uploads/2024/02/Color-Variation-Orange-Block-I-White-Background.png', site: '', date: '2025-07-01' },
]

var _leaderboard = [
  { name: 'FULL', data: _full },
  { name: 'VERIFIED', data: _verified },
]

// 目前仅支持img、text、rich-text和code
var _sections = [
  {
    title: 'Overview',
    subtitle: 'Introduction to NoCode-bench',
    content: [
      {
        type: 'img',
        content: 'https://raw.githubusercontent.com/ZJU-CTAG/NoCode-bench/refs/heads/main/doc/task.png'
      },
      {
        type: 'text',
        content: 'NoCode-bench is a benchmark designed to evaluate the ability of Large Language Models (LLMs) to perform no-code feature addition using natural language documentation as input. Unlike prior benchmarks that focus on bug fixing or general issue resolution, NoCode-bench targets a new paradigm where feature development is driven by documentation changes in real-world software projects.',
      },
      {
        type: 'text',
        content: 'Each instance takes user-facing documentation changes as input and expects the model to generate corresponding code changes. The implementation is validated using developer-written test cases.',
      }
    ]
  },
  {
    title: 'How to submit',
    subtitle: '',
    content: [
      {
        type: 'rich-text',
        content: 'Prepare a .jsonl file. Each record must contain at least the keys instance_id and model_patch. Email the file to <b>dengle@zju.edu.cn</b>. We will evaluate your submission locally and update the leaderboard once the results are verified.',
      }
    ]
  },
  {
    title: 'Citation',
    subtitle: '',
    content: [
      {
        type: 'rich-text',
        content: 'If you found the <b>NoCode-bench</b> and <b>NoCode-bench Verified</b> helpful for your work, please cite as follows:',
      },
      {
        type: 'code',
        content: `@misc{deng2025nocode,
  title={NoCode-bench: A Benchmark for Evaluating Natural Language-Driven Feature Addition},
  author={Deng Le and Jiang Zhonghao and Cao Jialun and Pradel Michael and Liu Zhongxin},
  journal={arXiv preprint arXiv:2507.18130},
  year={2025}
}`,
      },
      {
        type: 'rich-text',
        content: 'Correspondence to: <u>dengle@zju.edu.cn</u>, <u>liu_zx@zju.edu.cn</u> and <u>zhonghao.j@zju.edu.cn</u>'
      }
    ]
  }
]

// public/data.js
window.__APP_DATA__ = {
  leaderboard: _leaderboard,
  sections: _sections,
}
