import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiRequest } from '../api';
import { ChannelProfile, Video } from '../types';
import { useAuth } from '../context/AuthContext';
import { VideoCard } from '../components/VideoCard';
import { Bell, BellOff, PlusCircle, Video as VideoIcon } from 'lucide-react';

export const ChannelPage: React.FC = () => {
  const { username } = useParams<{ username: string }>();
  const { user } = useAuth();

  const [channel, setChannel] = useState<ChannelProfile | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'videos' | 'about'>('videos');
  const [subscribing, setSubscribing] = useState(false);

  useEffect(() => {
    if (!username) return;

    const fetchChannelData = async () => {
      setLoading(true);
      try {
        const [profile, vids] = await Promise.all([
          apiRequest<ChannelProfile>(`/channels/${username}`),
          apiRequest<Video[]>(`/channels/${username}/videos`),
        ]);
        setChannel(profile);
        setVideos(vids);
      } catch (err) {
        console.error('Failed to load channel:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchChannelData();
  }, [username]);

  const handleSubscribe = async () => {
    if (!user || !channel) return;
    setSubscribing(true);
    try {
      const res = await apiRequest(`/channels/${channel.username}/subscribe`, {
        method: 'POST',
      });
      setChannel({
        ...channel,
        is_subscribed: res.is_subscribed,
        subscribers_count: res.subscribers_count,
      });
    } catch (err) {
      console.error(err);
    } finally {
      setSubscribing(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto space-y-6 animate-pulse">
        <div className="h-40 bg-gray-200 dark:bg-[#272727] rounded-2xl"></div>
        <div className="flex gap-6 items-center">
          <div className="w-24 h-24 rounded-full bg-gray-200 dark:bg-[#272727]"></div>
          <div className="space-y-3 flex-1">
            <div className="h-6 bg-gray-200 dark:bg-[#272727] rounded w-1/3"></div>
            <div className="h-4 bg-gray-200 dark:bg-[#272727] rounded w-1/4"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!channel) {
    return (
      <div className="text-center py-20 text-gray-500">
        <p className="text-xl font-semibold">Канал не найден</p>
        <Link to="/" className="text-blue-500 text-sm mt-2 inline-block">
          Вернуться на главную
        </Link>
      </div>
    );
  }

  const isOwner = user?.username === channel.username;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Channel Banner */}
      <div className="h-36 sm:h-48 rounded-2xl bg-gradient-to-r from-red-600 via-purple-600 to-blue-600 flex items-end p-6 text-white shadow-inner"></div>

      {/* Channel Header Profile */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 px-2">
        <div className="flex items-center gap-5">
          <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-gradient-to-tr from-purple-600 to-blue-600 text-white font-bold flex items-center justify-center text-3xl sm:text-4xl shadow-md">
            {channel.username.slice(0, 1).toUpperCase()}
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold">{channel.channel_name}</h1>
            <div className="flex items-center gap-2 text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
              <span>@{channel.username}</span>
              <span>•</span>
              <span>{channel.subscribers_count} подписчиков</span>
              <span>•</span>
              <span>{videos.length} видео</span>
            </div>
            {channel.channel_description && (
              <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-300 mt-2 line-clamp-1 max-w-xl">
                {channel.channel_description}
              </p>
            )}
          </div>
        </div>

        {/* Subscribe or Upload Button */}
        <div className="flex items-center gap-3">
          {isOwner ? (
            <Link
              to="/upload"
              className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-black text-white dark:bg-white dark:text-black font-semibold text-sm hover:opacity-90 transition"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Загрузить видео</span>
            </Link>
          ) : user ? (
            <button
              onClick={handleSubscribe}
              disabled={subscribing}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-full text-sm font-semibold transition ${
                channel.is_subscribed
                  ? 'bg-gray-200 dark:bg-[#272727] text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-[#383838]'
                  : 'bg-black text-white dark:bg-white dark:text-black hover:opacity-90'
              }`}
            >
              {channel.is_subscribed ? (
                <>
                  <BellOff className="w-4 h-4" />
                  <span>Вы подписаны</span>
                </>
              ) : (
                <>
                  <Bell className="w-4 h-4" />
                  <span>Подписаться</span>
                </>
              )}
            </button>
          ) : (
            <Link
              to="/login"
              className="px-6 py-2.5 rounded-full bg-black text-white dark:bg-white dark:text-black text-sm font-semibold hover:opacity-90"
            >
              Подписаться
            </Link>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-[#272727] flex gap-8 px-2 text-sm font-medium">
        <button
          onClick={() => setActiveTab('videos')}
          className={`pb-3 border-b-2 transition ${
            activeTab === 'videos'
              ? 'border-black dark:border-white font-semibold'
              : 'border-transparent text-gray-500 hover:text-black dark:hover:text-white'
          }`}
        >
          Видео ({videos.length})
        </button>
        <button
          onClick={() => setActiveTab('about')}
          className={`pb-3 border-b-2 transition ${
            activeTab === 'about'
              ? 'border-black dark:border-white font-semibold'
              : 'border-transparent text-gray-500 hover:text-black dark:hover:text-white'
          }`}
        >
          О канале
        </button>
      </div>

      {/* Tab Contents */}
      {activeTab === 'videos' ? (
        videos.length === 0 ? (
          <div className="text-center py-20 text-gray-500 space-y-2">
            <VideoIcon className="w-12 h-12 mx-auto stroke-1" />
            <p className="text-lg">На этом канале пока нет опубликованных видео</p>
            {isOwner && (
              <Link
                to="/upload"
                className="inline-block mt-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                Опубликовать первое видео
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-8">
            {videos.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
        )
      ) : (
        <div className="max-w-2xl bg-gray-50 dark:bg-[#181818] p-6 rounded-2xl space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              Описание
            </h3>
            <p className="mt-2 text-sm leading-relaxed whitespace-pre-wrap">
              {channel.channel_description || 'Автор пока не добавил описание своего канала.'}
            </p>
          </div>
          <div className="pt-4 border-t border-gray-200 dark:border-[#272727] text-xs text-gray-500 space-y-1">
            <p>Дата регистрации: {new Date(channel.created_at).toLocaleDateString()}</p>
            <p>Подписчиков: {channel.subscribers_count}</p>
          </div>
        </div>
      )}
    </div>
  );
};
