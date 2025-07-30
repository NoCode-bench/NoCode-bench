import { useState } from 'react'
// import TaskImg from '../../assets/task.png'
import linkIcon from '../../assets/link.png'
import './index.css'

// const sections = [
//   {
//     title: 'Overview',
//     subtitle: 'Introduction to NoCode-bench',
//     content: [
//       {
//         type: 'img',
//         content: 'https://raw.githubusercontent.com/ZJU-CTAG/NoCode-bench/refs/heads/main/doc/task.png'
//       },
//       {
//         type: 'text',
//         content: 'NoCode-bench is a benchmark designed to evaluate the ability of Large Language Models (LLMs) to perform no-code feature addition using natural language documentation as input. Unlike prior benchmarks that focus on bug fixing or general issue resolution, NoCode-bench targets a new paradigm where feature development is driven by documentation changes in real-world software projects.',
//       },
//       {
//         type: 'text',
//         content: 'Each instance takes user-facing documentation changes as input and expects the model to generate corresponding code changes. The implementation is validated using developer-written test cases.',
//       }
//     ]
//   },
//   {
//     title: 'How to submit',
//     subtitle: '',
//     content: [
//       {
//         type: 'rich-text',
//         content: 'Prepare a .jsonl file. Each record must contain at least the keys instance_id and model_patch. Email the file to <b>dengle@zju.edu.cn</b>. We will evaluate your submission locally and update the leaderboard once the results are verified.',
//       }
//     ]
//   }
// ]


const paragragh2html = {
  'img': (content) => {
    return (
      <div className='img-wrapper'>
        <img src={content} alt='' />
      </div>
    )
  },
  'text': (content) => {
    return (
      <p>{content}</p>
    )
  },
  'rich-text': (content) => {
    return (
      <p dangerouslySetInnerHTML={{ __html: content }} />
    )
  }
}

const descList = [
  {
    title: 'github',
    href: 'https://github.com/ZJU-CTAG/NoCode-bench',
    badge: 'https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=white&style=for-the-badge'
  },
  {
    title: 'arxiv',
    href: 'https://arxiv.org/abs/2507.18130',
    badge: 'https://img.shields.io/badge/arXiv-900000?logo=arxiv&logoColor=white&style=for-the-badge'
  },
  {
    title: 'huggingface',
    href: 'https://huggingface.co/organizations/NoCode-bench/share/eoNAdddemrNANPlrWcrwltvMjkxsXgBSmX',
    badge: 'https://img.shields.io/badge/HuggingFace-FFD21E?logo=huggingface&logoColor=white&style=for-the-badge'
  },
  {
    title: 'dockerhub',
    href: '',
    badge: 'https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white&style=for-the-badge'
  }
]

const Header = () => {
  return (
    <header>
      <div className="title">NoCode-bench Leaderboard</div>
      <div className="sub-title">A benchmark designed for no-code feature addition on real-world software projects. </div>
      <div className="desc-list">
        {
          descList.map((item, index) => {
            return (
              <a className="desc-item" href={item.href} key={index} target="_blank" rel="noreferrer">
                <img src={item.badge} alt={item.title} />
              </a>
            )
          })
        }
      </div>
    </header>
  )
}
const Footer = () => {
  return (
    <footer>
      <div>
        made with 🥰 by <a href="http://www.icsoft.zju.edu.cn/" target="_blank" rel="noreferrer">ICSoft</a>
      </div>
    </footer>
  )
}

const TableWrapper = ({ leaderboard }) => {
  const [activeBench, setActiveBench] = useState(0)

  return (
    <section>
      <div className="table-wrapper">
        <div className="table-title">
          <div className='section-title'>Leaderboard</div>
          <div className='bench-btns'>
            {
              leaderboard.map((item, index) => {
                return (
                  <div
                    className={`bench-btn ${activeBench === index ? 'bench-btn__active' : ''}`}
                    key={index} onClick={() => {
                      setActiveBench(index)
                    }}
                  >
                    {item.name}
                  </div>
                )
              })
            }
          </div>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>RANK</th>
                <th>METHOD</th>
                <th>MODEL</th>
                <th>%RESOLVED</th>
                <th>ORG</th>
                <th>SITE</th>
                <th>DATE</th>
              </tr>
            </thead>
            <tbody>
              {
                leaderboard[activeBench]?.['data'].map((item, index) => {
                  return (
                    <tr key={index}>
                      <td className='td-sm'>
                        <div
                          className={`rank-badge rank-${index + 1}`}
                        >{index + 1}</div>
                      </td>
                      <td>{item.method}</td>
                      <td>{item.model}</td>
                      <td className='td-mid'>{item.resolved}</td>
                      <td className='td-sm'>
                        {item.org ?
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }} href={item.org} target="_blank" rel="noopener noreferrer">
                            <img className='link-img' src={item.org} alt="Visit site" />
                          </div> :
                          '--'
                        }
                      </td>
                      <td className='td-sm'>
                        {item.site ?
                          <a style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }} href={item.site} target="_blank" rel="noopener noreferrer">
                            <img className='link-img' src={linkIcon} alt="Visit site" />
                          </a> :
                          '--'
                        }
                      </td>
                      <td style={{
                        color: '#888',
                        fontSize: '16px'
                      }}>{item.date}</td>
                    </tr>
                  )
                })
              }
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

const SectionWrapper = ({ title = '', subtitle = '', children }) => {
  return (
    <section className="section">
      <div className="section-title-row">
        <div className="section-title">{title}</div>
        {subtitle && <div className="section-subtitle">{subtitle}</div>}
      </div>
      <div className="section-content">
        {children}
      </div>
    </section>
  )
}

const Index = ({ leaderboard=[], sections=[] }) => {

  console.log(leaderboard)
  return (
    <>
      {/* 头部信息区域 */}
      <Header />
      <main>
        {/* 表格区域 */}
        <TableWrapper leaderboard={leaderboard} />
        {/* 信息区域 */}
        <>
          {
            sections.map((item, index) => {
              return (
                <SectionWrapper key={index} title={item.title} subtitle={item.subtitle}>
                  {item.content.map((it, idx) => {
                    let paraType = it.type
                    if (!paragragh2html.hasOwnProperty(paraType)) {
                      paraType = 'text'
                    }
                    return typeof it.content === 'string' && paragragh2html[paraType](it.content)
                  })}
                </SectionWrapper>
              )
            })
          }
        </>
        {/* <SectionWrapper title='Overview' subtitle='Introduction to NoCode-bench'>
          <div className='img-wrapper'>
            <img src={TaskImg} alt="task" />
          </div>
          <p>NoCode-bench is a benchmark designed to evaluate the ability of Large Language Models (LLMs) to perform no-code feature addition using natural language documentation as input. Unlike prior benchmarks that focus on bug fixing or general issue resolution, NoCode-bench targets a new paradigm where feature development is driven by documentation changes in real-world software projects.</p>
          <p>Each instance takes user-facing documentation changes as input and expects the model to generate corresponding code changes. The implementation is validated using developer-written test cases.</p>
          <p></p>
        </SectionWrapper>
        <SectionWrapper title='How to submit'>
          <p>Prepare a .jsonl file. Each record must contain at least the keys instance_id and model_patch.
            Email the file to <b>dengle@zju.edu.cn</b>.
            We will evaluate your submission locally and update the leaderboard once the results are verified.</p>
        </SectionWrapper> */}
      </main>
      <Footer />
    </>
  )
}

export default Index