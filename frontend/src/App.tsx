/** Root layout: ambient background, navbar, split editor / results panes. */
import { Footer } from './components/layout/Footer';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { EditorPanel } from './components/editor/EditorPanel';
import { ToastViewport } from './components/ui/Toast';
import { ResultsPanel } from './components/visualization/ResultsPanel';
import { ErrorBoundary } from './components/shared/ErrorBoundary';

export default function App() {
  return (
    <div className="relative flex min-h-full flex-col">
      <div className="orb orb-1" aria-hidden />
      <div className="orb orb-2" aria-hidden />
      <div className="orb orb-3" aria-hidden />
      <Navbar />
      <main className="relative z-10 grid flex-1 grid-cols-1 gap-4 p-3 md:p-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div className="flex min-h-0 flex-col lg:sticky lg:top-5 lg:h-[calc(100vh-7.5rem)]">
          <ErrorBoundary label="editor">
            <EditorPanel />
          </ErrorBoundary>
        </div>
        <ErrorBoundary label="visualisation">
          <ResultsPanel />
        </ErrorBoundary>
      </main>
      <Footer />
      <Sidebar />
      <ToastViewport />
    </div>
  );
}
