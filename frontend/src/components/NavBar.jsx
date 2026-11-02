import { Link, useLocation } from 'react-router-dom';
import { Activity } from 'lucide-react';
import './NavBar.css';

const NavBar = () => {
  const location = useLocation();

  return (
    <nav className="navbar glass-panel">
      <div className="nav-container">
        <Link to="/" className="nav-logo">
          <Activity size={28} className="logo-icon" />
          <span className="text-gradient">SQAM</span>
        </Link>
        <ul className="nav-menu">
          <li className="nav-item">
            <Link to="/" className={location.pathname === '/' ? 'nav-link active' : 'nav-link'}>Home</Link>
          </li>
          <li className="nav-item">
            <Link to="/how-it-works" className={location.pathname === '/how-it-works' || location.pathname === '/about' ? 'nav-link active' : 'nav-link'}>How It Works</Link>
          </li>
          <li className="nav-item">
            <Link to="/analytics" className={location.pathname === '/analytics' ? 'nav-link active' : 'nav-link'}>Analytics</Link>
          </li>
          <li className="nav-item">
            <Link to="/scanner" className={location.pathname === '/scanner' ? 'nav-link active nav-scan-link' : 'nav-link nav-scan-link'}>Repository Scanner</Link>
          </li>
        </ul>
      </div>
    </nav>
  );
};

export default NavBar;
