/** Page: frosted nav → hero (live demo) → resizable workspace (editor | results). */
import { useEffect } from 'react';

import { ChatPanel } from './components/chat/ChatPanel';
import { EditorPanel } from './components/editor/EditorPanel';
import { Hero } from './components/hero/Hero';
import { Footer } from './components/layout/Footer';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { SplitPane } from './components/layout/SplitPane';
import { ErrorBoundary } from './components/shared/ErrorBoundary';
import { ToastViewport } from './components/ui/Toast';
import { ResultsPanel } from './components/visualization/ResultsPanel';
import { useAppStore } from './stores/appStore';
import { loadJSON, saveJSON } from './utils/storage';

const SEEN_KEY = 'codelens.seenHero';

/** Returning users land on the workspace; the hero stays one scroll up. */
function useLandOnWorkspace() {
  useEffect(() => {
    if (loadJSON<boolean>(SEEN_KEY, false) || window.location.hash.startsWith('#code=')) {
      requestAnimationFrame(() => document.getElementById('workspace')?.scrollIntoView({ block: 'start' }));
    }
    const unsub = useAppStore.subscribe((s, prev) => {
      if (s.status === 'analyzing' && prev.status !== 'analyzing') {
        saveJSON(SEEN_KEY, true);
        const ws = document.getElementById('workspace');
        if (ws && ws.getBoundingClientRect().top > 80) ws.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
    return unsub;
  }, []);
}

export default function App() {
  useLandOnWorkspace();
  return (
    <div className="min-h-full">
      <Navbar />
      <Hero />
      <main id="workspace" className="mx-auto max-w-[1600px] scroll-mt-[52px] px-3 pb-6 pt-4 md:px-5">
        <SplitPane
          storageKey="codelens.split"
          className="lg:h-[calc(100vh-52px-2rem)]"
          left={
            <ErrorBoundary label="editor">
              <EditorPanel />
            </ErrorBoundary>
          }
          right={
            <ErrorBoundary label="visualisation">
              <ResultsPanel />
            </ErrorBoundary>
          }
        />
      </main>
      <Footer />
      <Sidebar />
      <ChatPanel />
      <ToastViewport />
    </div>
  );
}
