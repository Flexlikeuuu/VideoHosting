import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Menu,
  Search,
  Sun,
  Moon,
  ShieldAlert,
  User as UserIcon,
  LogOut,
  PlusCircle,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

interface HeaderProps {
  onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [profileOpen, setProfileOpen] = useState(false);
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <header className="fixed top-0 left-0 right-0 h-14 bg-white dark:bg-[#0f0f0f] border-b border-gray-200 dark:border-[#272727] z-50 flex items-center justify-between px-4">
      {/* Left: Burger + Logo */}
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-[#272727] transition"
        >
          <Menu className="w-5 h-5 text-gray-700 dark:text-gray-200" />
        </button>

        <Link to="/" className="flex items-center gap-1">
          <div className="w-8 h-6 bg-[#FF0000] rounded-lg flex items-center justify-center">
            <div className="w-0 h-0 border-y-[4px] border-y-transparent border-l-[8px] border-l-white ml-0.5"></div>
          </div>
          <span className="font-bold text-lg tracking-tight flex items-center">
            YouTube <span className="text-[10px] uppercase font-semibold text-gray-500 ml-1">Clone</span>
          </span>
        </Link>
      </div>

      {/* Center: Search Bar */}
      <form onSubmit={handleSearch} className="flex-1 max-w-xl mx-4 hidden sm:flex">
        <div className="flex w-full">
          <input
            type="text"
            placeholder="Введите запрос"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 text-sm bg-transparent border border-gray-300 dark:border-[#303030] rounded-l-full focus:outline-none focus:border-blue-500 dark:focus:border-blue-500 placeholder-gray-500"
          />
          <button
            type="submit"
            className="px-6 bg-gray-100 dark:bg-[#222] border border-l-0 border-gray-300 dark:border-[#303030] rounded-r-full hover:bg-gray-200 dark:hover:bg-[#272727] transition flex items-center justify-center"
          >
            <Search className="w-4 h-4 text-gray-600 dark:text-gray-300" />
          </button>
        </div>
      </form>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={toggleTheme}
          title="Сменить тему"
          className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-[#272727] text-gray-700 dark:text-gray-200"
        >
          {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        {user ? (
          <>
            {/* Create video button */}
            <Link
              to="/upload"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-100 dark:bg-[#272727] hover:bg-gray-200 dark:hover:bg-[#3f3f3f] text-sm font-medium transition"
            >
              <PlusCircle className="w-4 h-4 text-red-500" />
              <span className="hidden md:inline">Создать</span>
            </Link>

            {/* Moderator Badge */}
            {(user.role === 'moderator' || user.role === 'admin') && (
              <Link
                to="/moderation"
                title="Панель модерации"
                className="p-2 rounded-full hover:bg-red-50 dark:hover:bg-red-950/30 text-red-600 transition"
              >
                <ShieldAlert className="w-5 h-5" />
              </Link>
            )}

            {/* User Profile dropdown */}
            <div className="relative">
              <button
                onClick={() => setProfileOpen(!profileOpen)}
                className="w-8 h-8 rounded-full bg-blue-600 text-white font-semibold flex items-center justify-center text-sm ml-1"
              >
                {user.username.slice(0, 1).toUpperCase()}
              </button>

              {profileOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-[#282828] border border-gray-200 dark:border-[#383838] rounded-xl shadow-xl py-2 z-50 text-sm">
                  <div className="px-4 py-2 border-b border-gray-200 dark:border-[#383838]">
                    <p className="font-semibold">{user.channel_name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">@{user.username}</p>
                    <span className="inline-block mt-1 text-[10px] px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 font-medium">
                      {user.role}
                    </span>
                  </div>

                  <Link
                    to={`/channel/${user.username}`}
                    onClick={() => setProfileOpen(false)}
                    className="flex items-center gap-3 px-4 py-2 hover:bg-gray-100 dark:hover:bg-[#383838]"
                  >
                    <UserIcon className="w-4 h-4 text-gray-500" />
                    <span>Мой канал</span>
                  </Link>

                  <button
                    onClick={async () => {
                      setProfileOpen(false);
                      await logout();
                      navigate('/');
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 text-left"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Выйти</span>
                  </button>
                </div>
              )}
            </div>
          </>
        ) : (
          <Link
            to="/login"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-blue-500 text-blue-600 dark:text-blue-400 text-sm font-medium hover:bg-blue-50 dark:hover:bg-blue-950/30 transition"
          >
            <UserIcon className="w-4 h-4" />
            <span>Войти</span>
          </Link>
        )}
      </div>
    </header>
  );
};
