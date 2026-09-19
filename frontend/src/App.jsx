import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import NavBar from './components/NavBar';
import Home from './pages/Home';
import About from './pages/About';
import Predictor from './pages/Predictor';
import Analytics from './pages/Analytics';
import Scanner from './pages/Scanner';
import './index.css';

function App() {
  return (
    <Router>
      <NavBar />
      <div className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/predictor" element={<Predictor />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/scanner" element={<Scanner />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
