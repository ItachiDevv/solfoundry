import React from 'react';
import ReactDOM from 'react-dom/client';
import { SiteLayout } from './components/layout/SiteLayout';
import './index.css';

/**
 * Root entry point for the SolFoundry frontend.
 * Wraps the app in SiteLayout for responsive header, sidebar, and footer.
 * Global styles including responsive.css are imported via index.css.
 *
 * @see SiteLayout
 */
/** Root entry point — renders the SolFoundry app and imports global styles including responsive.css */
function App() {
  return (
    <SiteLayout currentPath="/">
      <div id="solfoundry-app" />
    </SiteLayout>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
