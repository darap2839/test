import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Calendar, ChevronRight, Download, FileText, Folder, History, Pencil, Save, Tag, X } from 'lucide-react';
import { documentsApi } from '../api/client';

const typeLabels = {
  policy: 'Политика',
  procedure: 'Процедура',
  role_profile: 'Профиль должности',
  template: 'Шаблон',
  guide: 'Руководство'
};

const statusLabels = {
  draft: 'Черновик',
  published: 'Опубликован',
  archived: 'В архиве'
};

const versionFieldLabels = {
  title: 'Название',
  description: 'Описание',
  doc_type: 'Тип',
  department: 'Отдел',
  role: 'Должность',
  tags: 'Теги',
  access_level: 'Уровень доступа',
  content_text: 'Содержание',
  status: 'Статус'
};

const formatVersionDate = (value) => new Intl.DateTimeFormat('ru-RU', {
  dateStyle: 'medium',
  timeStyle: 'short'
}).format(new Date(value));

export default function KnowledgeDocumentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [documentItem, setDocumentItem] = useState(null);
  const [formData, setFormData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [versions, setVersions] = useState([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [selectedVersionLoading, setSelectedVersionLoading] = useState(false);

  useEffect(() => {
    const loadDocument = async () => {
      try {
        const data = await documentsApi.getDocument(id);
        setDocumentItem(data);
      } catch (loadError) {
        setError(loadError.message || 'Не удалось загрузить документ');
      } finally {
        setLoading(false);
      }
    };
    loadDocument();
  }, [id]);

  const startEditing = () => {
    setFormData({
      title: documentItem.title || '',
      description: documentItem.description || '',
      doc_type: documentItem.doc_type || 'guide',
      department: documentItem.department || '',
      role: documentItem.role || '',
      content_text: documentItem.content_text || ''
    });
    setEditing(true);
  };

  const saveDocument = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      const updated = await documentsApi.updateDocument(documentItem.id, formData);
      setDocumentItem(updated);
      setEditing(false);
    } catch (saveError) {
      setError(saveError.message || 'Не удалось сохранить изменения');
    } finally {
      setSaving(false);
    }
  };

  const downloadDocument = async () => {
    try {
      const blob = await documentsApi.getDocumentFile(documentItem.id, true);
      const url = URL.createObjectURL(blob);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = documentItem.file_name || `document-${documentItem.id}`;
      window.document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(downloadError.message || 'Не удалось скачать файл');
    }
  };

  const openHistory = async () => {
    setHistoryOpen(true);
    setSelectedVersion(null);
    setVersionsLoading(true);
    setHistoryError('');
    try {
      setVersions(await documentsApi.getDocumentVersions(documentItem.id));
    } catch (historyLoadError) {
      setHistoryError(historyLoadError.message || 'Не удалось загрузить историю версий');
    } finally {
      setVersionsLoading(false);
    }
  };

  const openVersion = async (versionNumber) => {
    setSelectedVersionLoading(true);
    setHistoryError('');
    try {
      setSelectedVersion(await documentsApi.getDocumentVersion(documentItem.id, versionNumber));
    } catch (versionLoadError) {
      setHistoryError(versionLoadError.message || 'Не удалось загрузить версию');
    } finally {
      setSelectedVersionLoading(false);
    }
  };

  const closeHistory = () => {
    setHistoryOpen(false);
    setSelectedVersion(null);
    setHistoryError('');
  };

  if (loading) return <div className="page-container"><div className="loading-state">Загрузка...</div></div>;

  if (!documentItem) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <FileText size={48} />
          <p>{error || 'Документ не найден'}</p>
          <button className="primary-button" onClick={() => navigate('/knowledge-base')}>Вернуться к списку</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container knowledge-document-page">
      <div className="page-header knowledge-document-header">
        <div className="knowledge-document-heading">
          <button className="icon-button" aria-label="Вернуться к базе знаний" onClick={() => navigate('/knowledge-base')}>
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1>{documentItem.title}</h1>
            <p>Документ базы знаний</p>
          </div>
        </div>
        <div className="knowledge-document-actions">
          {!editing && (
            <button className="secondary-button" type="button" onClick={openHistory}>
              <History size={18} /> История версий
            </button>
          )}
          {editing ? (
            <button className="secondary-button" type="button" onClick={() => setEditing(false)}>
              <X size={18} /> Отмена
            </button>
          ) : (
            <button className="secondary-button" type="button" onClick={startEditing}>
              <Pencil size={18} /> Редактировать
            </button>
          )}
          <button className="primary-button" type="button" onClick={downloadDocument} disabled={!documentItem.file_name}>
            <Download size={18} /> Скачать
          </button>
        </div>
      </div>

      <div className="knowledge-document-status">
        <span className={`badge badge-${documentItem.status === 'published' ? 'green' : documentItem.status === 'archived' ? 'gray' : 'yellow'}`}>
          {statusLabels[documentItem.status] || documentItem.status}
        </span>
      </div>

      {error && <div className="login-error" role="alert">{error}</div>}

      {editing ? (
        <form className="card knowledge-document-editor" onSubmit={saveDocument}>
          <label><span>Название *</span><input required value={formData.title} onChange={event => setFormData({ ...formData, title: event.target.value })} /></label>
          <label><span>Описание</span><textarea rows={3} value={formData.description} onChange={event => setFormData({ ...formData, description: event.target.value })} /></label>
          <div className="knowledge-document-editor-row">
            <label><span>Тип</span><select value={formData.doc_type} onChange={event => setFormData({ ...formData, doc_type: event.target.value })}>{Object.entries(typeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label><span>Отдел</span><input value={formData.department} onChange={event => setFormData({ ...formData, department: event.target.value })} /></label>
          </div>
          <label><span>Содержание</span><textarea rows={16} value={formData.content_text} onChange={event => setFormData({ ...formData, content_text: event.target.value })} /></label>
          <div className="knowledge-document-editor-footer">
            <button className="primary-button" type="submit" disabled={saving}><Save size={18} /> {saving ? 'Сохранение...' : 'Сохранить'}</button>
          </div>
        </form>
      ) : (
        <div className="knowledge-document-layout">
          <main className="knowledge-document-main">
            {documentItem.description && <section className="card"><h2>Краткое описание</h2><p>{documentItem.description}</p></section>}
            <section className="card">
              <h2><FileText size={20} /> Содержание документа</h2>
              <div
                className="knowledge-document-content"
                role="region"
                aria-label="Содержание документа"
                tabIndex={0}
              >
                {documentItem.content_text || 'В документе нет извлечённого текста.'}
              </div>
            </section>
          </main>
          <aside className="knowledge-document-sidebar">
            <section className="card">
              <h3>Информация</h3>
              <dl className="knowledge-document-info">
                <div><Tag size={19} /><dt>Тип</dt><dd>{typeLabels[documentItem.doc_type] || documentItem.doc_type}</dd></div>
                {documentItem.department && <div><Folder size={19} /><dt>Отдел</dt><dd>{documentItem.department}</dd></div>}
                <div><Calendar size={19} /><dt>Добавлен</dt><dd>{new Date(documentItem.created_at).toLocaleDateString()}</dd></div>
              </dl>
            </section>
            <section className="card">
              <h3>Исходный файл</h3>
              <div className="knowledge-document-file"><FileText size={20} /><span>{documentItem.file_name}</span></div>
            </section>
          </aside>
        </div>
      )}

      {historyOpen && (
        <div className="knowledge-history-backdrop" onClick={closeHistory}>
          <aside
            className="knowledge-history-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="knowledge-history-title"
            onClick={event => event.stopPropagation()}
          >
            <header className="knowledge-history-header">
              <div>
                {selectedVersion && (
                  <button
                    type="button"
                    className="knowledge-history-back"
                    onClick={() => setSelectedVersion(null)}
                  >
                    <ArrowLeft size={17} /> Ко всем версиям
                  </button>
                )}
                <h2 id="knowledge-history-title">
                  <History size={22} />
                  {selectedVersion ? `Версия ${selectedVersion.version_number}` : 'История версий'}
                </h2>
                <p>{documentItem.title}</p>
              </div>
              <button type="button" className="icon-button" aria-label="Закрыть историю" onClick={closeHistory}>
                <X size={20} />
              </button>
            </header>

            <div className="knowledge-history-body">
              {historyError && <div className="login-error" role="alert">{historyError}</div>}
              {(versionsLoading || selectedVersionLoading) && <div className="loading-state">Загрузка...</div>}

              {!versionsLoading && !selectedVersion && versions.length === 0 && !historyError && (
                <div className="knowledge-history-empty">
                  <History size={36} />
                  <p>История появится после первого изменения документа.</p>
                </div>
              )}

              {!versionsLoading && !selectedVersion && versions.length > 0 && (
                <div className="knowledge-version-list">
                  {versions.map(version => (
                    <button
                      type="button"
                      key={version.version_number}
                      className="knowledge-version-item"
                      onClick={() => openVersion(version.version_number)}
                    >
                      <div>
                        <strong>Версия {version.version_number}</strong>
                        <span>{formatVersionDate(version.created_at)}</span>
                        <small>
                          {(version.changed_fields || []).map(field => versionFieldLabels[field] || field).join(', ') || 'Изменения не указаны'}
                        </small>
                      </div>
                      <ChevronRight size={20} />
                    </button>
                  ))}
                </div>
              )}

              {!selectedVersionLoading && selectedVersion && (
                <article className="knowledge-version-preview">
                  <div className="knowledge-version-meta">
                    <span>{formatVersionDate(selectedVersion.created_at)}</span>
                    <span>{statusLabels[selectedVersion.status] || selectedVersion.status}</span>
                  </div>
                  <div className="knowledge-version-fields">
                    {(selectedVersion.changed_fields || []).map(field => (
                      <span key={field}>{versionFieldLabels[field] || field}</span>
                    ))}
                  </div>
                  <section>
                    <h3>{selectedVersion.title}</h3>
                    {selectedVersion.description && <p>{selectedVersion.description}</p>}
                  </section>
                  <section>
                    <h3>Содержание версии</h3>
                    <div className="knowledge-version-content">
                      {selectedVersion.content_text || 'В этой версии нет текста.'}
                    </div>
                  </section>
                </article>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
