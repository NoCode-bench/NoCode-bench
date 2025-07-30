import { useEffect, useState } from 'react';
import Home from './views/Home'

function App() {
  const [leaderboard, setLeaderboard] = useState([])
  const [sections, setSections] = useState([])

  useEffect(() => {
    const script = document.createElement('script');
    script.src = `./data.js?t=${Date.now()}`;  // 动态时间戳
    script.async = true;
    document.body.appendChild(script);
    script.onload = () => {
      // 假设 data.js 里定义了 window.__APP_DATA__
      setLeaderboard(window.__APP_DATA__.leaderboard);
      setSections(window.__APP_DATA__.sections);
    };
    return () => {
      document.body.removeChild(script);
    };
  }, [])
  // 需要给排序leaderboard排序
  return (
    <Home leaderboard={leaderboard} sections={sections} />
  );
}

export default App;
