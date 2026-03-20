import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';

/** Root entry point — renders the SolFoundry app and imports global styles including responsive.css */
function App() {
  return <div id="solfoundry-app" />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
