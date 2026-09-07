import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import KnowledgeBase from '../../pages/KnowledgeBase';
import { documentsApi } from '../../api/client';

vi.mock('../../api/client', () => ({
  documentsApi: {
    getDocuments: vi.fn(),
    getDocumentFile: vi.fn(),
    updateDocument: vi.fn(),
    deleteDocument: vi.fn(),
    restoreDocument: vi.fn()
  }
}));

const documentItem = {
  id: 1,
  title: 'Регламент интервью',
  description: 'Порядок проведения интервью',
  content_text: 'Подготовьте вопросы до встречи.',
  doc_type: 'procedure',
  department: 'HR',
  status: 'published',
  file_name: 'interview.pdf',
  created_at: '2026-09-05T10:00:00Z'
};

const renderKnowledgeBase = (initialEntry = '/knowledge-base') => render(
  <MemoryRouter initialEntries={[initialEntry]}>
    <KnowledgeBase />
  </MemoryRouter>
);

describe('KnowledgeBase document preview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    documentsApi.getDocuments.mockResolvedValue([documentItem]);
    documentsApi.updateDocument.mockResolvedValue({});
    documentsApi.restoreDocument.mockResolvedValue({});
  });

  it('открывает документ на отдельной странице', async () => {
    render(
      <MemoryRouter initialEntries={['/knowledge-base']}>
        <Routes>
          <Route path="/knowledge-base" element={<KnowledgeBase />} />
          <Route path="/knowledge-base/documents/:id" element={<div>Страница документа</div>} />
        </Routes>
      </MemoryRouter>
    );
    const title = await screen.findByRole('heading', { name: documentItem.title });

    fireEvent.click(title);

    expect(screen.getByText('Страница документа')).toBeInTheDocument();
  });

  it('не показывает внутренние тип и статус на карточке', async () => {
    const internalValuesDocument = { ...documentItem, doc_type: 'guide', status: 'draft' };
    documentsApi.getDocuments.mockResolvedValue([internalValuesDocument]);
    renderKnowledgeBase();

    await screen.findByRole('heading', { name: internalValuesDocument.title });
    expect(screen.queryByText('guide')).not.toBeInTheDocument();
    expect(screen.queryByText('draft')).not.toBeInTheDocument();
    expect(screen.getAllByText(internalValuesDocument.department)).toHaveLength(2);
  });

  it('восстанавливает фильтры из URL', async () => {
    renderKnowledgeBase('/knowledge-base?type=procedure&department=HR');

    expect(screen.getByLabelText('Тип документа')).toHaveValue('procedure');
    expect(screen.getByLabelText('Отдел')).toHaveValue('HR');
    await waitFor(() => expect(documentsApi.getDocuments).toHaveBeenCalled());
    const params = documentsApi.getDocuments.mock.calls.at(-1)[0];
    expect(params.get('doc_type')).toBe('procedure');
    expect(params.get('department')).toBe('HR');
    expect(params.get('archived')).toBe('false');
  });

  it('переключается на архив и сохраняет раздел в URL', async () => {
    renderKnowledgeBase();
    await screen.findByRole('heading', { name: documentItem.title });

    fireEvent.click(screen.getByRole('tab', { name: /архив/i }));

    await waitFor(() => {
      const params = documentsApi.getDocuments.mock.calls.at(-1)[0];
      expect(params.get('archived')).toBe('true');
    });
    expect(screen.getByRole('tab', { name: /архив/i })).toHaveAttribute('aria-selected', 'true');
  });

  it('открывает архивный раздел из URL', async () => {
    renderKnowledgeBase('/knowledge-base?view=archive');

    expect(screen.getByRole('tab', { name: /архив/i })).toHaveAttribute('aria-selected', 'true');
    await waitFor(() => {
      const params = documentsApi.getDocuments.mock.calls.at(-1)[0];
      expect(params.get('archived')).toBe('true');
    });
  });

  it('открывает корзину из дополнительного меню и запрашивает удалённые документы', async () => {
    renderKnowledgeBase();
    await screen.findByRole('heading', { name: documentItem.title });

    expect(screen.queryByRole('tab', { name: /удалённые/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /дополнительные разделы/i }));
    fireEvent.click(screen.getByRole('button', { name: /корзина/i }));

    await waitFor(() => {
      const params = documentsApi.getDocuments.mock.calls.at(-1)[0];
      expect(params.get('deleted')).toBe('true');
      expect(params.has('archived')).toBe(false);
    });
    expect(screen.getByText('Здесь хранятся удалённые документы')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: `Действия с документом ${documentItem.title}` })).toBeInTheDocument();
  });

  it('восстанавливает документ из удалённых', async () => {
    const deletedDocument = { ...documentItem, is_deleted: true };
    documentsApi.getDocuments.mockResolvedValue([deletedDocument]);
    renderKnowledgeBase('/knowledge-base?view=deleted');
    await screen.findByRole('heading', { name: deletedDocument.title });

    fireEvent.click(screen.getByRole('button', { name: `Действия с документом ${deletedDocument.title}` }));
    fireEvent.click(screen.getByRole('button', { name: /восстановить/i }));

    await waitFor(() => {
      expect(documentsApi.restoreDocument).toHaveBeenCalledWith(deletedDocument.id);
      expect(documentsApi.getDocuments).toHaveBeenCalledTimes(2);
    });
  });

  it('восстанавливает архивный документ как черновик', async () => {
    const archivedDocument = { ...documentItem, status: 'archived' };
    documentsApi.getDocuments.mockResolvedValue([archivedDocument]);
    renderKnowledgeBase('/knowledge-base?view=archive');
    await screen.findByRole('heading', { name: archivedDocument.title });

    fireEvent.click(screen.getByRole('button', { name: `Действия с документом ${archivedDocument.title}` }));
    fireEvent.click(screen.getByRole('button', { name: /восстановить/i }));

    await waitFor(() => {
      expect(documentsApi.updateDocument).toHaveBeenCalledWith(archivedDocument.id, { status: 'draft' });
      expect(documentsApi.getDocuments).toHaveBeenCalledTimes(2);
    });
  });

  it('отправляет поиск только после задержки', async () => {
    vi.useFakeTimers();
    renderKnowledgeBase();
    await act(async () => {});
    const initialCalls = documentsApi.getDocuments.mock.calls.length;

    fireEvent.change(screen.getByLabelText('Поиск по документам'), {
      target: { value: 'отпуск' }
    });
    expect(documentsApi.getDocuments).toHaveBeenCalledTimes(initialCalls);

    await act(async () => {
      vi.advanceTimersByTime(350);
    });
    expect(documentsApi.getDocuments).toHaveBeenCalledTimes(initialCalls + 1);
    expect(documentsApi.getDocuments.mock.calls.at(-1)[0].get('search')).toBe('отпуск');
    vi.useRealTimers();
  });
});
