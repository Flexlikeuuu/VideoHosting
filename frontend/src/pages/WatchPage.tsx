import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ThumbsUp,
  ThumbsDown,
  Flag,
  Lock,
  Users,
  Trash2,
  CheckCircle2,
} from 'lucide-react';
import { apiRequest } from '../api';
import { Video, Comment, VideoAccessGrant } from '../types';
import { useAuth } from '../context/AuthContext';
import { formatDate, formatViews } from '../utils';

export const WatchPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();

  const [video, setVideo] = useState<Video | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Social states
  const [userReaction, setUserReaction] = useState<number | null>(null);
  const [likesCount, setLikesCount] = useState(0);
  const [dislikesCount, setDislikesCount] = useState(0);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [subscribersCount, setSubscribersCount] = useState(0);

  // Description accordion
  const [descExpanded, setDescExpanded] = useState(false);

  // Comments
  const [comments, setComments] = useState<Comment[]>([]);
  const [commentText, setCommentText] = useState('');
  const [commentSubmitting, setCommentSubmitting] = useState(false);

  // Modals
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [reportReason, setReportReason] = useState('');
  const [reportSuccess, setReportSuccess] = useState(false);

  const [accessModalOpen, setAccessModalOpen] = useState(false);
  const [accessTargetUser, setAccessTargetUser] = useState('');
  const [accessList, setAccessList] = useState<VideoAccessGrant[]>([]);
  const [accessError, setAccessError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const fetchVideoData = async () => {
      setLoading(true);
      setError(null);
      try {
        const v = await apiRequest<Video>(`/videos/${id}`);
        setVideo(v);
        setLikesCount(v.likes_count);
        setDislikesCount(v.dislikes_count);

        // Fetch channel info
        const ch = await apiRequest(`/channels/${v.owner.username}`);
        setIsSubscribed(ch.is_subscribed);
        setSubscribersCount(ch.subscribers_count);

        // Record view with deduplication
        apiRequest(`/videos/${id}/view`, { method: 'POST' }).catch(() => {});

        // Fetch comments
        const comms = await apiRequest<Comment[]>(`/videos/${id}/comments`);
        setComments(comms);
      } catch (err: any) {
        setError(err.message || 'Ошибка загрузки видео');
      } finally {
        setLoading(false);
      }
    };
    fetchVideoData();
  }, [id]);

  const handleReaction = async (val: number) => {
    if (!user || !id) return;
    const nextVal = userReaction === val ? 0 : val;
    try {
      const res = await apiRequest(`/videos/${id}/react`, {
        method: 'POST',
        body: JSON.stringify({ value: nextVal }),
      });
      setLikesCount(res.likes_count);
      setDislikesCount(res.dislikes_count);
      setUserReaction(res.user_reaction);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSubscribe = async () => {
    if (!user || !video) return;
    try {
      const res = await apiRequest(`/channels/${video.owner.username}/subscribe`, {
        method: 'POST',
      });
      setIsSubscribed(res.is_subscribed);
      setSubscribersCount(res.subscribers_count);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim() || !id || !user) return;
    setCommentSubmitting(true);
    try {
      const newComm = await apiRequest<Comment>(`/videos/${id}/comments`, {
        method: 'POST',
        body: JSON.stringify({ content: commentText.trim() }),
      });
      setComments([newComm, ...comments]);
      setCommentText('');
    } catch (err) {
      console.error(err);
    } finally {
      setCommentSubmitting(false);
    }
  };

  const handleDeleteComment = async (commentId: string) => {
    try {
      await apiRequest(`/comments/${commentId}`, { method: 'DELETE' });
      setComments(comments.filter((c) => c.id !== commentId));
    } catch (err) {
      console.error(err);
    }
  };

  const handleReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !reportReason.trim()) return;
    try {
      await apiRequest(`/videos/${id}/report`, {
        method: 'POST',
        body: JSON.stringify({ reason: reportReason.trim() }),
      });
      setReportSuccess(true);
      setTimeout(() => {
        setReportSuccess(false);
        setReportModalOpen(false);
        setReportReason('');
      }, 1500);
    } catch (err) {
      console.error(err);
    }
  };

  const loadAccessList = async () => {
    if (!id) return;
    try {
      const list = await apiRequest<VideoAccessGrant[]>(`/videos/${id}/access`);
      setAccessList(list);
    } catch (err) {
      console.error(err);
    }
  };

  const handleGrantAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !accessTargetUser.trim()) return;
    setAccessError(null);
    try {
      await apiRequest(`/videos/${id}/access`, {
        method: 'POST',
        body: JSON.stringify({ username_or_email: accessTargetUser.trim() }),
      });
      setAccessTargetUser('');
      await loadAccessList();
    } catch (err: any) {
      setAccessError(err.message || 'Ошибка выдачи доступа');
    }
  };

  const handleRevokeAccess = async (userId: string) => {
    if (!id) return;
    try {
      await apiRequest(`/videos/${id}/access/${userId}`, { method: 'DELETE' });
      await loadAccessList();
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto space-y-4 animate-pulse">
        <div className="aspect-video bg-gray-200 dark:bg-[#202020] rounded-2xl w-full"></div>
        <div className="h-6 bg-gray-200 dark:bg-[#202020] rounded w-2/3"></div>
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="text-center py-20">
        <div className="inline-flex p-4 rounded-full bg-red-100 dark:bg-red-950/30 text-red-600 mb-3">
          <Lock className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold">Видео недоступно</h2>
        <p className="text-gray-500 mt-1">{error || 'У вас нет прав для просмотра этого видео.'}</p>
        <Link to="/" className="inline-block mt-4 px-4 py-2 bg-blue-600 text-white rounded-full text-sm font-medium">
          На главную
        </Link>
      </div>
    );
  }

  const isOwner = Boolean(user && user.id === video.owner.id);

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      {/* HTML5 Video Player with HTTP Range streaming */}
      <div className="relative aspect-video rounded-2xl overflow-hidden bg-black shadow-lg">
        <video
          controls
          autoPlay
          className="w-full h-full object-contain"
          src={`/api/v1/videos/${video.id}/stream`}
          poster={`/api/v1/videos/${video.id}/thumbnail`}
        />
      </div>

      {/* Video Title */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          {video.visibility === 'private' && (
            <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20 font-medium">
              <Lock className="w-3.5 h-3.5" />
              Доступ по приглашению
            </span>
          )}
          <h1 className="text-xl font-bold">{video.title}</h1>
        </div>
      </div>

      {/* Channel Block & Reaction Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 dark:border-[#272727] pb-4">
        {/* Channel Info + Subscribe */}
        <div className="flex items-center gap-3">
          <Link to={`/channel/${video.owner.username}`}>
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-purple-600 to-blue-600 text-white font-bold flex items-center justify-center">
              {video.owner.username.slice(0, 1).toUpperCase()}
            </div>
          </Link>
          <div>
            <Link to={`/channel/${video.owner.username}`} className="font-semibold text-sm hover:underline">
              {video.owner.channel_name}
            </Link>
            <p className="text-xs text-gray-500">{subscribersCount} подписчиков</p>
          </div>

          {user && user.id !== video.owner.id && (
            <button
              onClick={handleSubscribe}
              className={`ml-4 px-4 py-2 rounded-full text-sm font-medium transition ${
                isSubscribed
                  ? 'bg-gray-200 dark:bg-[#272727] text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-[#3f3f3f]'
                  : 'bg-black text-white dark:bg-white dark:text-black hover:opacity-90'
              }`}
            >
              {isSubscribed ? 'Вы подписаны' : 'Подписаться'}
            </button>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {/* Likes / Dislikes pill */}
          <div className="flex items-center bg-gray-100 dark:bg-[#272727] rounded-full overflow-hidden text-sm">
            <button
              onClick={() => handleReaction(1)}
              className={`flex items-center gap-1.5 px-3.5 py-2 hover:bg-gray-200 dark:hover:bg-[#3f3f3f] transition ${
                userReaction === 1 ? 'text-blue-600 dark:text-blue-400 font-bold' : ''
              }`}
            >
              <ThumbsUp className="w-4 h-4" />
              <span>{likesCount}</span>
            </button>
            <div className="w-[1px] h-5 bg-gray-300 dark:bg-[#3f3f3f]"></div>
            <button
              onClick={() => handleReaction(-1)}
              title={dislikesCount > 0 ? `${dislikesCount} отметок «не нравится»` : 'Не нравится'}
              className={`flex items-center gap-1.5 px-3.5 py-2 hover:bg-gray-200 dark:hover:bg-[#3f3f3f] transition ${
                userReaction === -1 ? 'text-red-600 dark:text-red-400 font-bold' : ''
              }`}
            >
              <ThumbsDown className="w-4 h-4" />
              {dislikesCount > 0 && <span className="text-xs">{dislikesCount}</span>}
            </button>
          </div>

          {/* Manage Access Button (Owner only on private video) */}
          {isOwner && video.visibility === 'private' && (
            <button
              onClick={() => {
                setAccessModalOpen(true);
                loadAccessList();
              }}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 text-sm font-medium transition"
            >
              <Users className="w-4 h-4" />
              <span>Доступ ({accessList.length})</span>
            </button>
          )}

          {/* Report Button */}
          {user && (
            <button
              onClick={() => setReportModalOpen(true)}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-gray-100 dark:bg-[#272727] hover:bg-gray-200 dark:hover:bg-[#3f3f3f] text-sm font-medium transition"
            >
              <Flag className="w-4 h-4" />
              <span className="hidden md:inline">Пожаловаться</span>
            </button>
          )}
        </div>
      </div>

      {/* Description Box */}
      <div
        onClick={() => setDescExpanded(!descExpanded)}
        className="bg-gray-100 dark:bg-[#272727] rounded-xl p-3 text-sm cursor-pointer hover:bg-gray-200 dark:hover:bg-[#333] transition"
      >
        <div className="font-semibold text-xs text-gray-600 dark:text-gray-300 flex gap-2">
          <span>{formatViews(video.views_count)}</span>
          <span>{formatDate(video.created_at)}</span>
        </div>
        <p className={`mt-2 whitespace-pre-wrap text-sm ${!descExpanded ? 'line-clamp-2' : ''}`}>
          {video.description || 'Нет описания.'}
        </p>
        <button className="font-bold text-xs mt-2 text-gray-500 dark:text-gray-400">
          {descExpanded ? 'Свернуть' : 'Еще'}
        </button>
      </div>

      {/* Comments Section */}
      <div className="space-y-4 pt-2">
        <h3 className="font-bold text-base">{comments.length} комментариев</h3>

        {/* Add comment input */}
        {user ? (
          <form onSubmit={handleAddComment} className="flex gap-3">
            <div className="w-9 h-9 rounded-full bg-blue-600 text-white font-semibold flex items-center justify-center shrink-0 text-sm">
              {user.username.slice(0, 1).toUpperCase()}
            </div>
            <div className="flex-1 flex flex-col items-end gap-2">
              <input
                type="text"
                placeholder="Оставьте комментарий..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                className="w-full bg-transparent border-b border-gray-300 dark:border-[#3f3f3f] focus:border-black dark:focus:border-white focus:outline-none py-1 text-sm"
              />
              {commentText.trim() && (
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setCommentText('')}
                    className="px-3 py-1.5 text-xs font-semibold rounded-full hover:bg-gray-100 dark:hover:bg-[#272727]"
                  >
                    Отмена
                  </button>
                  <button
                    type="submit"
                    disabled={commentSubmitting}
                    className="px-4 py-1.5 text-xs font-semibold rounded-full bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    Оставить комментарий
                  </button>
                </div>
              )}
            </div>
          </form>
        ) : (
          <p className="text-sm text-gray-500">
            <Link to="/login" className="text-blue-500 hover:underline">
              Войдите
            </Link>
            , чтобы оставить комментарий.
          </p>
        )}

        {/* Comments List */}
        <div className="space-y-4 pt-2">
          {comments.map((comm) => {
            const canDelete = Boolean(
              user &&
                (user.id === comm.author.id ||
                  user.id === video.owner.id ||
                  user.role === 'moderator' ||
                  user.role === 'admin')
            );

            return (
              <div key={comm.id} className="flex gap-3 group">
                <Link to={`/channel/${comm.author.username}`}>
                  <div className="w-9 h-9 rounded-full bg-gray-400 text-white font-semibold flex items-center justify-center shrink-0 text-sm">
                    {comm.author.username.slice(0, 1).toUpperCase()}
                  </div>
                </Link>
                <div className="flex-1 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs">@{comm.author.username}</span>
                    <span className="text-[11px] text-gray-500">{formatDate(comm.created_at)}</span>
                  </div>
                  <p className="mt-1 whitespace-pre-wrap">{comm.content}</p>
                </div>

                {canDelete && (
                  <button
                    onClick={() => handleDeleteComment(comm.id)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 text-gray-400 hover:text-red-500 transition"
                    title="Удалить"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* --- Report Modal --- */}
      {reportModalOpen && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#202020] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold">Пожаловаться на видео</h3>
            {reportSuccess ? (
              <div className="flex items-center gap-2 text-green-600 py-4">
                <CheckCircle2 className="w-6 h-6" />
                <span>Жалоба успешно отправлена на модерацию</span>
              </div>
            ) : (
              <form onSubmit={handleReport} className="space-y-4">
                <textarea
                  placeholder="Опишите причину жалобы..."
                  value={reportReason}
                  onChange={(e) => setReportReason(e.target.value)}
                  required
                  rows={4}
                  className="w-full p-3 rounded-lg bg-gray-50 dark:bg-[#181818] border border-gray-300 dark:border-[#383838] focus:outline-none focus:border-red-500 text-sm"
                />
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setReportModalOpen(false)}
                    className="px-4 py-2 text-sm rounded-full hover:bg-gray-100 dark:hover:bg-[#272727]"
                  >
                    Отмена
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 text-sm font-semibold rounded-full bg-red-600 text-white hover:bg-red-700"
                  >
                    Отправить
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* --- Manage Private Video Access Modal --- */}
      {accessModalOpen && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-[#202020] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <Users className="w-5 h-5 text-amber-500" />
                <span>Управление доступом к видео</span>
              </h3>
              <button
                onClick={() => setAccessModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 text-sm"
              >
                Закрыть
              </button>
            </div>

            <p className="text-xs text-gray-500">
              Выдайте доступ по логину или email. Пользователи смогут просматривать приватное видео.
            </p>

            <form onSubmit={handleGrantAccess} className="flex gap-2">
              <input
                type="text"
                placeholder="Логин или Email пользователя"
                value={accessTargetUser}
                onChange={(e) => setAccessTargetUser(e.target.value)}
                required
                className="flex-1 px-3 py-2 rounded-lg bg-gray-50 dark:bg-[#181818] border border-gray-300 dark:border-[#383838] text-sm focus:outline-none focus:border-blue-500"
              />
              <button
                type="submit"
                className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
              >
                Выдать
              </button>
            </form>

            {accessError && <p className="text-xs text-red-500">{accessError}</p>}

            <div className="space-y-2 max-h-60 overflow-y-auto pt-2">
              <p className="text-xs font-semibold text-gray-500 uppercase">Пользователи с доступом:</p>
              {accessList.length === 0 ? (
                <p className="text-xs text-gray-400 py-2">Список доступа пуст</p>
              ) : (
                accessList.map((grant) => (
                  <div
                    key={grant.id}
                    className="flex items-center justify-between p-2 rounded-lg bg-gray-50 dark:bg-[#181818] text-sm"
                  >
                    <div>
                      <p className="font-semibold text-xs">{grant.user.channel_name}</p>
                      <p className="text-[11px] text-gray-400">@{grant.user.username} • {grant.user.email}</p>
                    </div>
                    <button
                      onClick={() => handleRevokeAccess(grant.user.id)}
                      className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 rounded"
                      title="Отозвать доступ"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
