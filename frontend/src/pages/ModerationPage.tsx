import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiRequest } from '../api';
import { Report } from '../types';
import { useAuth } from '../context/AuthContext';
import { formatDate } from '../utils';
import { ShieldAlert, CheckCircle, EyeOff, ExternalLink } from 'lucide-react';

export const ModerationPage: React.FC = () => {
  const { user } = useAuth();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [commentInput, setCommentInput] = useState<{ [key: string]: string }>({});

  const fetchReports = async () => {
    setLoading(true);
    try {
      const data = await apiRequest<Report[]>('/moderation/reports');
      setReports(data);
    } catch (err) {
      console.error('Failed to load moderation reports:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleResolve = async (reportId: string, action: 'hide' | 'dismiss') => {
    setResolvingId(reportId);
    try {
      await apiRequest(`/moderation/reports/${reportId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({
          action,
          comment: commentInput[reportId] || undefined,
        }),
      });
      await fetchReports();
    } catch (err) {
      console.error('Failed to resolve report:', err);
    } finally {
      setResolvingId(null);
    }
  };

  if (!user || (user.role !== 'moderator' && user.role !== 'admin')) {
    return (
      <div className="max-w-md mx-auto text-center py-20 space-y-4">
        <ShieldAlert className="w-16 h-16 mx-auto text-red-500" />
        <h2 className="text-xl font-bold">Доступ запрещен</h2>
        <p className="text-sm text-gray-500">
          Эта панель предназначена только для модераторов и администраторов платформы.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="border-b border-gray-200 dark:border-[#272727] pb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-red-500" />
            <span>Панель модерации</span>
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Очередь жалоб пользователей на видеоконтент и нарушение правил платформы.
          </p>
        </div>
        <span className="text-xs px-3 py-1 rounded-full bg-red-100 dark:bg-red-950/50 text-red-600 font-semibold">
          Очередь: {reports.filter((r) => r.status === 'pending').length}
        </span>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="animate-pulse p-4 rounded-xl bg-gray-200 dark:bg-[#202020] h-28"></div>
          ))}
        </div>
      ) : reports.length === 0 ? (
        <div className="text-center py-20 text-gray-500 space-y-2">
          <CheckCircle className="w-12 h-12 mx-auto text-green-500 stroke-1" />
          <p className="text-lg font-semibold">Жалоб нет</p>
          <p className="text-sm">Все отправленные жалобы рассмотрены. Чистота и порядок!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((report) => (
            <div
              key={report.id}
              className={`p-5 rounded-2xl border transition ${
                report.status === 'pending'
                  ? 'border-amber-200 dark:border-amber-900/40 bg-amber-50/20 dark:bg-amber-950/10'
                  : 'border-gray-200 dark:border-[#272727] bg-white dark:bg-[#181818]'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 dark:border-[#272727] pb-3 mb-3">
                <div className="flex items-center gap-2 text-sm">
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded font-semibold uppercase ${
                      report.status === 'pending'
                        ? 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300'
                        : report.status === 'resolved'
                        ? 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                    }`}
                  >
                    {report.status === 'pending'
                      ? 'Ожидает проверки'
                      : report.status === 'resolved'
                      ? 'Скрыто'
                      : 'Отклонено'}
                  </span>
                  <span className="text-xs text-gray-400">•</span>
                  <span className="text-xs text-gray-500">Отправлено: {formatDate(report.created_at)}</span>
                  <span className="text-xs text-gray-400">•</span>
                  <span className="text-xs text-gray-500">
                    Автор жалобы: <span className="font-medium text-gray-700 dark:text-gray-300">@{report.reporter.username}</span>
                  </span>
                </div>

                <Link
                  to={`/watch/${report.video_id}`}
                  target="_blank"
                  className="inline-flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400 font-semibold hover:underline"
                >
                  <span>Просмотреть видео</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
              </div>

              {/* Reason */}
              <div className="space-y-1">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Причина жалобы:</p>
                <p className="text-sm text-gray-800 dark:text-gray-200 font-medium bg-gray-50 dark:bg-[#202020] p-3 rounded-xl border border-gray-200 dark:border-[#2c2c2c]">
                  {report.reason}
                </p>
              </div>

              {/* Actions for pending reports */}
              {report.status === 'pending' ? (
                <div className="mt-4 pt-3 border-t border-gray-100 dark:border-[#272727] flex flex-col sm:flex-row items-center justify-between gap-3">
                  <input
                    type="text"
                    placeholder="Комментарий модератора (опционально)"
                    value={commentInput[report.id] || ''}
                    onChange={(e) =>
                      setCommentInput({ ...commentInput, [report.id]: e.target.value })
                    }
                    className="w-full sm:flex-1 px-3 py-2 text-xs rounded-lg bg-gray-50 dark:bg-[#121212] border border-gray-300 dark:border-[#383838] focus:outline-none focus:border-blue-500"
                  />
                  <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                    <button
                      onClick={() => handleResolve(report.id, 'dismiss')}
                      disabled={resolvingId === report.id}
                      className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-[#272727] text-gray-700 dark:text-gray-200 text-xs font-semibold hover:bg-gray-300 dark:hover:bg-[#383838] disabled:opacity-50 transition"
                    >
                      Отклонить жалобу
                    </button>
                    <button
                      onClick={() => handleResolve(report.id, 'hide')}
                      disabled={resolvingId === report.id}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-600 text-white text-xs font-semibold hover:bg-red-700 disabled:opacity-50 transition"
                    >
                      <EyeOff className="w-3.5 h-3.5" />
                      <span>Скрыть видео</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-3 text-xs text-gray-400">
                  {report.moderator && (
                    <span>
                      Проверил: @{report.moderator.username}
                      {report.moderator_comment && ` • Комментарий: «${report.moderator_comment}»`}
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
