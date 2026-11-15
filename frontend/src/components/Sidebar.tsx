import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Home,
  PlaySquare,
  User,
  ShieldAlert,
  UploadCloud,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface SidebarProps {
  isOpen: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen }) => {
  const { user } = useAuth();

  const navItemClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-6 px-3 py-2.5 rounded-xl text-sm font-normal transition ${
      isActive
        ? 'bg-gray-100 dark:bg-[#272727] font-medium'
        : 'hover:bg-gray-100 dark:hover:bg-[#272727]'
    }`;

  if (!isOpen) {
    return (
      <aside className="fixed left-0 top-14 bottom-0 w-18 bg-white dark:bg-[#0f0f0f] border-r border-gray-200 dark:border-[#272727] hidden md:flex flex-col items-center py-2 z-40">
        <NavLink
          to="/"
          className={({ isActive }) =>
            `flex flex-col items-center justify-center w-16 py-3 rounded-lg text-[10px] ${
              isActive ? 'text-red-600' : 'text-gray-600 dark:text-gray-300'
            }`
          }
        >
          <Home className="w-5 h-5 mb-1" />
          <span>Главная</span>
        </NavLink>
        {user && (
          <NavLink
            to={`/channel/${user.username}`}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center w-16 py-3 rounded-lg text-[10px] ${
                isActive ? 'text-red-600' : 'text-gray-600 dark:text-gray-300'
              }`
            }
          >
            <User className="w-5 h-5 mb-1" />
            <span>Вы</span>
          </NavLink>
        )}
      </aside>
    );
  }

  return (
    <aside className="fixed left-0 top-14 bottom-0 w-60 bg-white dark:bg-[#0f0f0f] border-r border-gray-200 dark:border-[#272727] overflow-y-auto px-3 py-3 z-40 flex flex-col justify-between">
      <div className="space-y-1">
        <NavLink to="/" end className={navItemClass}>
          <Home className="w-5 h-5" />
          <span>Главная</span>
        </NavLink>

        {user && (
          <>
            <NavLink to={`/channel/${user.username}`} className={navItemClass}>
              <PlaySquare className="w-5 h-5" />
              <span>Мой канал</span>
            </NavLink>

            <NavLink to="/upload" className={navItemClass}>
              <UploadCloud className="w-5 h-5" />
              <span>Загрузка видео</span>
            </NavLink>
          </>
        )}

        {(user?.role === 'moderator' || user?.role === 'admin') && (
          <div className="pt-4 border-t border-gray-200 dark:border-[#272727]">
            <p className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
              Администрирование
            </p>
            <NavLink to="/moderation" className={navItemClass}>
              <ShieldAlert className="w-5 h-5 text-red-500" />
              <span>Модерация</span>
            </NavLink>
          </div>
        )}
      </div>

      <div className="p-3 text-xs text-gray-400 dark:text-gray-600 border-t border-gray-200 dark:border-[#272727]">
        YouTube Clone MVP © 2026
      </div>
    </aside>
  );
};
