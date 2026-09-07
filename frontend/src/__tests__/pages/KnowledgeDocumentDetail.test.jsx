import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import KnowledgeDocumentDetail from '../../pages/KnowledgeDocumentDetail';
import { documentsApi } from '../../api/client';

vi.mock('../../api/client', () => ({
  documentsApi: {
    getDocument: vi.fn(),
    getDocumentVersions: vi.fn(),
    getDocumentVersion: vi.fn(),
    getDocumentFile: vi.fn(),
    updateDocument: vi.fn()
  }
}));

const documentItem = {
  id: 7,
  title: 'Регламент интервью',
  description: 'Порядок проведения интервью',
  content_text: 'Подготовьте вопросы до встречи.',
  doc_type: 'procedure',
  department: 'HR',
  status: 'published',
  file_name: 'interview.pdf',
  created_at: '2026-09-05T10:00:00Z'
};

const versionSummary = {
  version_number: 1,
  changed_fields: ['title', 'content_text'],
  changed_by_id: null,
  created_at: '2026-09-06T12:30:00Z'
};

const documentVersion = {
  ...versionSummary,
  document_id: 7,
  title: 'Первоначальный регламент',
  description: 'Первая редакция',
  content_text: 'Первоначальный текст документа.',
  doc_type: 'procedure',
  department: 'HR',
  role: null,
  tags: '',
  access_level: 'public',
  status: 'draft'
};

const renderPage = () => render(
  <MemoryRouter initialEntries={['/knowledge-base/documents/7']}>
    <Routes>
      <Route path="/knowledge-base/documents/:id" element={<KnowledgeDocumentDetail />} />
    </Routes>
  </MemoryRouter>
);

describe('KnowledgeDocumentDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    documentsApi.getDocument.mockResolvedValue(documentItem);
    documentsApi.getDocumentVersions.mockResolvedValue([versionSummary]);
    documentsApi.getDocumentVersion.mockResolvedValue(documentVersion);
  });

  it('показывает документ на отдельной странице в режиме чтения', async () => {
    renderPage();

    expect(await screen.findByRole('heading', { name: documentItem.title })).toBeInTheDocument();
    expect(screen.getByText(documentItem.content_text)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Содержание документа' })).toHaveAttribute('tabindex', '0');
    expect(screen.queryByDisplayValue(documentItem.title)).not.toBeInTheDocument();
  });

  it('включает редактирование только по отдельной кнопке', async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: /редактировать/i }));

    await waitFor(() => expect(screen.getByDisplayValue(documentItem.title)).toBeInTheDocument());
  });

  it('открывает историю и показывает выбранную версию только для чтения', async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: /история версий/i }));

    expect(await screen.findByRole('dialog', { name: /история версий/i })).toBeInTheDocument();
    expect(documentsApi.getDocumentVersions).toHaveBeenCalledWith(documentItem.id);
    fireEvent.click(screen.getByRole('button', { name: /версия 1/i }));

    expect(await screen.findByRole('heading', { name: documentVersion.title })).toBeInTheDocument();
    expect(screen.getByText(documentVersion.content_text)).toBeInTheDocument();
    expect(documentsApi.getDocumentVersion).toHaveBeenCalledWith(documentItem.id, 1);
    expect(screen.queryByRole('button', { name: /восстановить/i })).not.toBeInTheDocument();
  });
});
