var _full = [
  { method: "Huang", model: 99, resolved: 10, org: 'https://avatars.githubusercontent.com/u/166046056?s=200&v=4', site: 'zju', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: 'https://avatars.githubusercontent.com/u/166046056?s=200&v=4', site: 'zju', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: 'https://brand.illinois.edu/wp-content/uploads/2024/02/Color-Variation-Orange-Block-I-White-Background.png', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
]
var _verified = [
  { method: "Deng", model: 99, resolved: 10, org: '', site: 'zju', date: '2023-04-03' },
  { method: "Deng", model: 99, resolved: 10, org: '', site: 'zju', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
  { method: "Huang", model: 99, resolved: 10, org: '', site: '', date: '2023-04-03' },
]

var _leaderboard = [
  {name: 'FULL', data: _full},
  {name: 'Verified', data: _verified},
]

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
  }
]

  // public/data.js
  window.__APP_DATA__ = {
    leaderboard: _leaderboard,
    sections: _sections,
  }
