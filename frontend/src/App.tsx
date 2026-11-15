import React, { useState } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './pages/HomePage';
import { WatchPage } from './pages/WatchPage';
import { SearchPage } from './pages/SearchPage';
import { ChannelPage } from './pages/ChannelPage';
import { UploadPage } from './pages/UploadPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ModerationPage } from './pages/ModerationPage';

export const App: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();

  // On watch page, sidebar is collapsed by default for full-width player experience
  const isWatchPage = location.pathname.startsWith('/watch/');

  const toggleSidebar = () => {
    setSidebarOpen((prev) => !prev);
  };

  return (
    <div className="min-h-screen bg-white dark:bg-[#0f0f0f] text-gray-900 dark:text-gray-100 flex flex-col font-sans transition-colors duration-150">
      <Header onToggleSidebar={toggleSidebar} />

      <div className="flex pt-14 flex-1">
        {!isWatchPage && <Sidebar isOpen={sidebarOpen} />}

        <main
          className={`flex-1 p-4 sm:p-6 transition-all duration-200 overflow-x-hidden ${
            isWatchPage
              ? 'w-full'
              : sidebarOpen
              ? 'md:ml-60'
              : 'md:ml-18'
          }`}
        >
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/watch/:id" element={<WatchPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/channel/:username" element={<ChannelPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/moderation" element={<ModerationPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

export default App;
