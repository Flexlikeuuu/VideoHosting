import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiRequest } from '../api';
import { useAuth } from '../context/AuthContext';
import { AlertCircle, Lock, Mail, User as UserIcon, Tv } from 'lucide-react';

export const RegisterPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [channelName, setChannelName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Пароли не совпадают');
      return;
    }

    if (password.length < 6) {
      setError('Пароль должен содержать не менее 6 символов');
      return;
    }

    setLoading(true);
    try {
      const data = await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          username: username.trim(),
          email: email.trim(),
          password,
          channel_name: channelName.trim() || undefined,
        }),
      });
      login(data.user);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Ошибка регистрации');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[75vh] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md bg-white dark:bg-[#181818] border border-gray-200 dark:border-[#272727] rounded-2xl p-8 shadow-sm space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-9 bg-[#FF0000] rounded-xl mx-auto flex items-center justify-center">
            <div className="w-0 h-0 border-y-[6px] border-y-transparent border-l-[12px] border-l-white ml-0.5"></div>
          </div>
          <h1 className="text-2xl font-bold">Создать канал</h1>
          <p className="text-sm text-gray-500">Зарегистрируйтесь, чтобы стать автором на платформе</p>
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
              Имя пользователя (логин)
            </label>
            <div className="relative">
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="creator_99"
                pattern="^[a-zA-Z0-9_-]+$"
                title="Только латинские буквы, цифры, дефис и подчеркивание"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-transparent border border-gray-300 dark:border-[#383838] focus:border-blue-500 focus:outline-none text-sm"
              />
              <UserIcon className="w-4 h-4 text-gray-400 absolute left-3.5 top-3" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Электронная почта
            </label>
            <div className="relative">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="author@example.com"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-transparent border border-gray-300 dark:border-[#383838] focus:border-blue-500 focus:outline-none text-sm"
              />
              <Mail className="w-4 h-4 text-gray-400 absolute left-3.5 top-3" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Название канала (опционально)
            </label>
            <div className="relative">
              <input
                type="text"
                value={channelName}
                onChange={(e) => setChannelName(e.target.value)}
                placeholder="Мой Супер Канал"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-transparent border border-gray-300 dark:border-[#383838] focus:border-blue-500 focus:outline-none text-sm"
              />
              <Tv className="w-4 h-4 text-gray-400 absolute left-3.5 top-3" />
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
                placeholder="Минимум 6 символов"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-transparent border border-gray-300 dark:border-[#383838] focus:border-blue-500 focus:outline-none text-sm"
              />
              <Lock className="w-4 h-4 text-gray-400 absolute left-3.5 top-3" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Подтверждение пароля
            </label>
            <div className="relative">
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Повторите пароль"
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
            {loading ? 'Регистрация...' : 'Зарегистрироваться'}
          </button>
        </form>

        <div className="text-center pt-2 border-t border-gray-200 dark:border-[#272727]">
          <p className="text-sm text-gray-500">
            Уже есть аккаунт?{' '}
            <Link to="/login" className="text-blue-600 dark:text-blue-400 font-medium hover:underline">
              Войти
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
