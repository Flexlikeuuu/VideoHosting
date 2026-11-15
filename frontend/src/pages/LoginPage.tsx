import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiRequest } from '../api';
import { useAuth } from '../context/AuthContext';
import { AlertCircle, Lock, User as UserIcon } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          username_or_email: usernameOrEmail.trim(),
          password,
        }),
      });
      login(data.user);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Ошибка входа в систему');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white dark:bg-[#181818] border border-gray-200 dark:border-[#272727] rounded-2xl p-8 shadow-sm space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-9 bg-[#FF0000] rounded-xl mx-auto flex items-center justify-center">
            <div className="w-0 h-0 border-y-[6px] border-y-transparent border-l-[12px] border-l-white ml-0.5"></div>
          </div>
          <h1 className="text-2xl font-bold">Вход в аккаунт</h1>
          <p className="text-sm text-gray-500">Войдите, чтобы публиковать видео и оставлять комментарии</p>
        </div>

        {error && (
          <div className="flex items-center gap-3 p-3.5 rounded-xl bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Логин или Email
            </label>
            <div className="relative">
              <input
                type="text"
                required
                value={usernameOrEmail}
                onChange={(e) => setUsernameOrEmail(e.target.value)}
                placeholder="name@example.com или username"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-transparent border border-gray-300 dark:border-[#383838] focus:border-blue-500 focus:outline-none text-sm"
              />
              <UserIcon className="w-4 h-4 text-gray-400 absolute left-3.5 top-3" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Пароль
            </label>
            <div className="relative">
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-transparent border border-gray-300 dark:border-[#383838] focus:border-blue-500 focus:outline-none text-sm"
              />
              <Lock className="w-4 h-4 text-gray-400 absolute left-3.5 top-3" />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-full bg-blue-600 text-white font-semibold text-sm hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>

        <div className="text-center pt-2 border-t border-gray-200 dark:border-[#272727]">
          <p className="text-sm text-gray-500">
            Нет аккаунта?{' '}
            <Link to="/register" className="text-blue-600 dark:text-blue-400 font-medium hover:underline">
              Зарегистрироваться
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
