import React, { useState, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { UploadCloud, Image as ImageIcon, Lock, Globe, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const UploadPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [thumbFile, setThumbFile] = useState<File | null>(null);
  const [thumbPreview, setThumbPreview] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [visibility, setVisibility] = useState<'public' | 'private'>('public');

  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [createdVideoId, setCreatedVideoId] = useState<string | null>(null);

  const videoInputRef = useRef<HTMLInputElement>(null);
  const thumbInputRef = useRef<HTMLInputElement>(null);

  // File drop handler
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      handleVideoSelect(file);
    }
  };

  const handleVideoSelect = (file: File) => {
    // Basic validation
    if (!file.type.startsWith('video/') && !file.name.match(/\.(mp4|webm|mkv|mov)$/i)) {
      setError('Пожалуйста, выберите корректный видеофайл (MP4, WebM, MKV, MOV).');
      return;
    }
    setError(null);
    setVideoFile(file);
    if (!title) {
      // Auto-populate title from filename without extension
      const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '');
      setTitle(nameWithoutExt);
    }
  };

  const handleThumbSelect = (file: File) => {
    if (!file.type.startsWith('image/')) {
      setError('Превью должно быть изображением (JPEG, PNG, WebP).');
      return;
    }
    setThumbFile(file);
    const reader = new FileReader();
    reader.onload = (e) => {
      setThumbPreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!videoFile) {
      setError('Выберите видеофайл для загрузки');
      return;
    }
    if (!title.trim()) {
      setError('Введите название видео');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setError(null);

    const formData = new FormData();
    formData.append('video', videoFile);
    formData.append('title', title.trim());
    if (description.trim()) {
      formData.append('description', description.trim());
    }
    formData.append('visibility', visibility);
    if (thumbFile) {
      formData.append('thumbnail', thumbFile);
    }

    // Use XMLHttpRequest for real upload progress
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/v1/videos/upload');
    xhr.withCredentials = true;

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        setUploadProgress(percent);
      }
    };

    xhr.onload = () => {
      setIsUploading(false);
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const res = JSON.parse(xhr.responseText);
          setCreatedVideoId(res.id);
        } catch {
          navigate('/');
        }
      } else {
        let msg = 'Ошибка при загрузке видео';
        try {
          const res = JSON.parse(xhr.responseText);
          msg = res.detail || msg;
        } catch {}
        setError(msg);
      }
    };

    xhr.onerror = () => {
      setIsUploading(false);
      setError('Сетевая ошибка при загрузке видео. Проверьте соединение.');
    };

    xhr.send(formData);
  };

  if (!user) {
    return (
      <div className="max-w-md mx-auto text-center py-20 space-y-4">
        <UploadCloud className="w-16 h-16 mx-auto text-gray-400 stroke-1" />
        <h2 className="text-xl font-bold">Требуется авторизация</h2>
        <p className="text-sm text-gray-500">
          Чтобы загружать видео на платформу, пожалуйста, войдите в свой аккаунт.
        </p>
        <Link
          to="/login"
          className="inline-block px-6 py-2.5 rounded-full bg-blue-600 text-white font-medium text-sm hover:bg-blue-700"
        >
          Войти
        </Link>
      </div>
    );
  }

  if (createdVideoId) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4 bg-white dark:bg-[#181818] p-8 rounded-2xl border border-gray-200 dark:border-[#272727] shadow-sm">
        <CheckCircle2 className="w-16 h-16 mx-auto text-green-500" />
        <h2 className="text-2xl font-bold">Видео успешно загружено!</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Файл передан на фоновую обработку FFmpeg (транскодирование в H.264/AAC и генерация миниатюры).
          Видео появится в ленте сразу после завершения обработки.
        </p>
        <div className="flex justify-center gap-4 pt-4">
          <Link
            to={`/watch/${createdVideoId}`}
            className="px-6 py-2.5 rounded-full bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700"
          >
            Перейти к видео
          </Link>
          <button
            onClick={() => {
              setCreatedVideoId(null);
              setVideoFile(null);
              setThumbFile(null);
              setThumbPreview(null);
              setTitle('');
              setDescription('');
              setUploadProgress(0);
            }}
            className="px-6 py-2.5 rounded-full bg-gray-100 dark:bg-[#272727] text-sm font-semibold hover:bg-gray-200 dark:hover:bg-[#383838]"
          >
            Загрузить ещё одно
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-4 space-y-6">
      <div className="border-b border-gray-200 dark:border-[#272727] pb-4">
        <h1 className="text-2xl font-bold">Загрузка нового видео</h1>
        <p className="text-sm text-gray-500 mt-1">
          Загружайте видео в форматах MP4, WebM, MKV или MOV.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Drop zone */}
        {!videoFile ? (
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => videoInputRef.current?.click()}
            className="border-2 border-dashed border-gray-300 dark:border-[#383838] hover:border-blue-500 dark:hover:border-blue-500 rounded-2xl p-12 text-center cursor-pointer transition flex flex-col items-center justify-center space-y-4 bg-gray-50/50 dark:bg-[#121212]"
          >
            <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-[#202020] flex items-center justify-center text-gray-500">
              <UploadCloud className="w-8 h-8" />
            </div>
            <div>
              <p className="font-semibold text-base">Перетащите видеофайл сюда</p>
              <p className="text-xs text-gray-400 mt-1">или нажмите, чтобы выбрать на компьютере</p>
            </div>
            <span className="text-[11px] text-gray-400">MP4, WebM, MKV, MOV (до 500 МБ)</span>
            <input
              ref={videoInputRef}
              type="file"
              accept="video/mp4,video/webm,video/x-matroska,video/quicktime"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleVideoSelect(e.target.files[0]);
                }
              }}
            />
          </div>
        ) : (
          <div className="flex items-center justify-between p-4 rounded-xl bg-gray-100 dark:bg-[#202020] border border-gray-200 dark:border-[#303030]">
            <div className="flex items-center gap-3 overflow-hidden">
              <UploadCloud className="w-6 h-6 text-blue-500 shrink-0" />
              <div className="overflow-hidden">
                <p className="text-sm font-semibold truncate">{videoFile.name}</p>
                <p className="text-xs text-gray-400">
                  {(videoFile.size / (1024 * 1024)).toFixed(2)} МБ
                </p>
              </div>
            </div>
            <button
              type="button"
              disabled={isUploading}
              onClick={() => setVideoFile(null)}
              className="text-xs text-red-500 hover:underline px-2 py-1"
            >
              Заменить файл
            </button>
          </div>
        )}

        {/* Video metadata */}
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Название (обязательно)
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isUploading}
              required
              placeholder="Добавьте название, которое описывает ваше видео"
              className="w-full px-4 py-2.5 rounded-xl bg-transparent border border-gray-300 dark:border-[#383838] focus:border-blue-500 focus:outline-none text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Описание
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isUploading}
              rows={4}
              placeholder="Расскажите зрителям о своем видео"
              className="w-full px-4 py-2.5 rounded-xl bg-transparent border border-gray-300 dark:border-[#383838] focus:border-blue-500 focus:outline-none text-sm resize-none"
            />
          </div>

          {/* Visibility selection */}
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Параметры доступа
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label
                className={`flex items-start gap-3 p-4 rounded-xl border cursor-pointer transition ${
                  visibility === 'public'
                    ? 'border-blue-500 bg-blue-50/20 dark:bg-blue-950/20'
                    : 'border-gray-200 dark:border-[#303030] hover:bg-gray-50 dark:hover:bg-[#1a1a1a]'
                }`}
              >
                <input
                  type="radio"
                  name="visibility"
                  value="public"
                  checked={visibility === 'public'}
                  onChange={() => setVisibility('public')}
                  className="mt-1"
                />
                <div>
                  <div className="flex items-center gap-1.5 font-semibold text-sm">
                    <Globe className="w-4 h-4 text-green-500" />
                    <span>Открытый доступ (Public)</span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Видео доступно всем пользователям и отображается в ленте и поиске.
                  </p>
                </div>
              </label>

              <label
                className={`flex items-start gap-3 p-4 rounded-xl border cursor-pointer transition ${
                  visibility === 'private'
                    ? 'border-blue-500 bg-blue-50/20 dark:bg-blue-950/20'
                    : 'border-gray-200 dark:border-[#303030] hover:bg-gray-50 dark:hover:bg-[#1a1a1a]'
                }`}
              >
                <input
                  type="radio"
                  name="visibility"
                  value="private"
                  checked={visibility === 'private'}
                  onChange={() => setVisibility('private')}
                  className="mt-1"
                />
                <div>
                  <div className="flex items-center gap-1.5 font-semibold text-sm">
                    <Lock className="w-4 h-4 text-amber-500" />
                    <span>Ограниченный доступ (Private)</span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Видео можете смотреть только вы и пользователи, которым вы выдадите доступ.
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Custom thumbnail */}
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Значок видео (превью)
            </label>
            <p className="text-xs text-gray-400 mb-2">
              Если превью не выбрано, оно будет сгенерировано автоматически из видео через FFmpeg.
            </p>

            <div className="flex items-center gap-4">
              {thumbPreview ? (
                <div className="relative w-40 aspect-video rounded-lg overflow-hidden border border-gray-300 dark:border-[#383838]">
                  <img src={thumbPreview} alt="Превью" className="w-full h-full object-cover" />
                  <button
                    type="button"
                    onClick={() => {
                      setThumbFile(null);
                      setThumbPreview(null);
                    }}
                    className="absolute top-1 right-1 bg-black/70 text-white rounded-full p-1 text-xs hover:bg-red-600"
                  >
                    ✕
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => thumbInputRef.current?.click()}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-dashed border-gray-300 dark:border-[#383838] text-sm text-gray-600 dark:text-gray-300 hover:border-gray-500"
                >
                  <ImageIcon className="w-4 h-4" />
                  <span>Загрузить значок</span>
                </button>
              )}
              <input
                ref={thumbInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleThumbSelect(e.target.files[0]);
                  }
                }}
              />
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        {isUploading && (
          <div className="space-y-2 p-4 rounded-xl bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900/50">
            <div className="flex justify-between text-xs font-semibold text-blue-600 dark:text-blue-400">
              <span>Загрузка файла на сервер...</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 transition-all duration-200"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Submit */}
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-[#272727]">
          <button
            type="button"
            disabled={isUploading}
            onClick={() => navigate('/')}
            className="px-5 py-2.5 rounded-full text-sm font-medium hover:bg-gray-100 dark:hover:bg-[#272727]"
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={isUploading || !videoFile}
            className="px-6 py-2.5 rounded-full bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {isUploading ? 'Загрузка...' : 'Опубликовать'}
          </button>
        </div>
      </form>
    </div>
  );
};
