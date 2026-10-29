import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { ContactRound, MessageCircle, MessagesSquare, RefreshCw, Search, Send, ShieldCheck, UserRound } from 'lucide-react';
import { useAuth } from './auth';
import { createPrivateConversation, listMessagingReviewers, listPrivateConversations, listPrivateMessages, markPrivateConversationRead, sendPrivateMessage } from './api';
import type { MessagingReviewer, PrivateConversation, PrivateMessage } from './api';

type DirectoryView = 'conversations' | 'contacts';

function initials(name: string) {
  return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]?.toUpperCase() ?? '').join('') || '?';
}

function messageTime(value: string) {
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function dateTime(value: string) {
  return new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

export function MessagingPage() {
  const { user } = useAuth();
  const [reviewers, setReviewers] = useState<MessagingReviewer[]>([]);
  const [conversations, setConversations] = useState<PrivateConversation[]>([]);
  const [selected, setSelected] = useState('');
  const [messages, setMessages] = useState<PrivateMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [draft, setDraft] = useState('');
  const [search, setSearch] = useState('');
  const [directoryView, setDirectoryView] = useState<DirectoryView>('conversations');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const refreshConversations = useCallback(async () => {
    const rows = await listPrivateConversations();
    setConversations(rows);
    return rows;
  }, []);

  const refreshMessages = useCallback(async (conversationId: string, markRead = false) => {
    const page = await listPrivateMessages(conversationId);
    setMessages(page.items);
    setTotal(page.total);
    if (markRead) {
      await markPrivateConversationRead(conversationId, page.items.map((message) => message.id));
      await refreshConversations();
    }
  }, [refreshConversations]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError('');
    const work = user?.role === 'farmer'
      ? Promise.all([listMessagingReviewers(), listPrivateConversations()]).then(([available, existing]) => {
          if (!cancelled) {
            setReviewers(available); setConversations(existing);
            setDirectoryView(existing.length ? 'conversations' : 'contacts');
          }
        })
      : refreshConversations().then((existing) => { if (!cancelled) setConversations(existing); });
    void work.catch((reason: Error) => { if (!cancelled) setError(reason.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [user?.role, refreshConversations]);

  useEffect(() => {
    const timer = window.setInterval(() => { void refreshConversations().catch((reason: Error) => setError(reason.message)); }, 15000);
    return () => window.clearInterval(timer);
  }, [refreshConversations]);

  useEffect(() => {
    if (!selected) { setMessages([]); setTotal(0); return; }
    let cancelled = false;
    const load = async (markRead: boolean) => {
      try {
        const page = await listPrivateMessages(selected);
        if (cancelled) return;
        setMessages(page.items); setTotal(page.total); setError('');
        if (markRead) { await markPrivateConversationRead(selected, page.items.map((message) => message.id)); await refreshConversations(); }
      } catch (reason) { if (!cancelled) setError(reason instanceof Error ? reason.message : 'Messages could not be loaded.'); }
    };
    void load(true);
    const timer = window.setInterval(() => { void load(true); }, 15000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [selected, refreshConversations]);

  async function startConversation(reviewerId: string) {
    setError('');
    try {
      const conversation = await createPrivateConversation(reviewerId);
      const rows = await refreshConversations();
      setSelected(rows.find((row) => row.id === conversation.id)?.id ?? conversation.id);
      setDirectoryView('conversations');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Conversation could not be started.'); }
  }

  async function submitMessage(event: FormEvent) {
    event.preventDefault();
    if (!selected || !draft.trim()) return;
    setSending(true); setError('');
    try {
      await sendPrivateMessage(selected, draft.trim()); setDraft('');
      await refreshMessages(selected, true);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Message could not be sent.'); }
    finally { setSending(false); }
  }

  async function loadOlder() {
    if (!selected || messages.length >= total) return;
    try {
      const page = await listPrivateMessages(selected, messages.length, 50);
      setMessages((current) => [...page.items, ...current]);
      await markPrivateConversationRead(selected, page.items.map((message) => message.id));
      await refreshConversations();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Older messages could not be loaded.'); }
  }

  const active = conversations.find((conversation) => conversation.id === selected);
  const activeReviewer = active && user?.role === 'farmer' ? reviewers.find((reviewer) => reviewer.id === active.other_user_id) : undefined;
  const filteredConversations = useMemo(() => {
    const query = search.trim().toLowerCase();
    return conversations.filter((item) => !query || `${item.other_display_name} ${item.other_role} ${item.last_message ?? ''}`.toLowerCase().includes(query));
  }, [conversations, search]);
  const filteredReviewers = useMemo(() => {
    const query = search.trim().toLowerCase();
    return reviewers.filter((item) => !query || `${item.display_name} ${item.eligible_districts.join(' ')}`.toLowerCase().includes(query));
  }, [reviewers, search]);
  const unreadTotal = conversations.reduce((sum, item) => sum + item.unread_count, 0);

  return <>
    <header className="page-heading messages-page-heading">
      <div><span className="eyebrow">PRIVATE COMMUNICATION</span><h1>Messages</h1><p>Chat with CropPulse reviewers assigned to your farm district. Reviewer status does not confirm agricultural qualifications.</p></div>
      <button className="button button-secondary" onClick={() => { setError(''); void refreshConversations().catch((reason: Error) => setError(reason.message)); }}><RefreshCw size={15} /> Refresh</button>
    </header>
    {error && <div className="notice notice-error" role="alert">{error}</div>}
    {loading ? <div role="status" className="inline-state">Loading private messages…</div> : <div className="messaging-layout">
      <aside className="panel messaging-directory" aria-label="Message contacts and conversations">
        <div className="messaging-tabs" role="tablist" aria-label="Message list">
          <button type="button" role="tab" aria-selected={directoryView === 'conversations'} className={directoryView === 'conversations' ? 'active' : ''} onClick={() => { setDirectoryView('conversations'); setSearch(''); }}><MessagesSquare size={15} /> Conversations <span>{conversations.length}</span></button>
          {user?.role === 'farmer' && <button type="button" role="tab" aria-selected={directoryView === 'contacts'} className={directoryView === 'contacts' ? 'active' : ''} onClick={() => { setDirectoryView('contacts'); setSearch(''); }}><ContactRound size={15} /> Contacts</button>}
        </div>
        <label className="message-search"><Search size={16} /><span className="sr-only">Search {directoryView}</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={directoryView === 'contacts' ? 'Search reviewers…' : 'Search conversations…'} /></label>
        {directoryView === 'contacts' && user?.role === 'farmer' ? <section className="directory-section"><h2>CropPulse reviewers</h2>
          {filteredReviewers.length ? filteredReviewers.map((reviewer) => <article className="directory-person" key={reviewer.id}><div className="message-avatar reviewer-avatar">{initials(reviewer.display_name)}<i /></div><div className="directory-person-copy"><strong>{reviewer.display_name}</strong><small>CropPulse reviewer</small><small>{reviewer.eligible_districts.join(', ')}</small></div><button className="message-start-button" onClick={() => void startConversation(reviewer.id)}>{conversations.some((item) => item.other_user_id === reviewer.id) ? 'Open' : 'Message'}</button></article>) : <div className="directory-empty"><ContactRound size={20} /><strong>No eligible reviewers</strong><p>No active reviewer is assigned to the district of one of your farms.</p></div>}
        </section> : <section className="directory-section"><h2>Recent conversations</h2>
          {filteredConversations.length ? filteredConversations.map((conversation) => <button type="button" key={conversation.id} className={`directory-person conversation-choice${selected === conversation.id ? ' selected' : ''}`} onClick={() => setSelected(conversation.id)}><div className="message-avatar">{initials(conversation.other_display_name)}<i /></div><span className="directory-person-copy"><strong>{conversation.other_display_name}</strong><small>{conversation.other_role}</small><small className="conversation-preview">{conversation.last_message ?? 'No messages yet'}</small></span><span className="directory-time">{messageTime(conversation.last_message_at)}{conversation.unread_count > 0 && <b className="unread-badge" aria-label={`${conversation.unread_count} unread messages`}>{conversation.unread_count}</b>}</span></button>) : <div className="directory-empty"><MessageCircle size={20} /><strong>{search ? 'No matching conversations' : 'No conversations yet'}</strong><p>{search ? 'Try another name or message.' : user?.role === 'farmer' ? 'Choose Contacts to message an eligible reviewer.' : 'New private conversations will appear here.'}</p></div>}
        </section>}
        <div className="messaging-privacy-note"><ShieldCheck size={16} /><span>Private messages are visible only to their participants.</span></div>
      </aside>

      <section className="panel conversation-panel" aria-label="Conversation messages">
        {active ? <>
          <div className="conversation-title"><div className="conversation-person"><div className="message-avatar large-avatar">{initials(active.other_display_name)}<i /></div><div><h2>{active.other_display_name}</h2><p>{active.other_role}{activeReviewer ? ` · ${activeReviewer.eligible_districts.join(', ')}` : ''}</p></div></div><span className="panel-badge">Private conversation</span></div>
          {messages.length < total && <button className="text-button load-older-button" onClick={() => void loadOlder()}>Load older messages</button>}
          <div className="message-history" role="log" aria-live="polite" aria-label={`Messages with ${active.other_display_name}`}>
            {messages.length ? messages.map((message) => <article key={message.id} className={`message-row${message.sender_id === user?.id ? ' message-row-own' : ''}`}><div className="message-avatar message-avatar-small">{message.sender_id === user?.id ? initials(user.display_name) : initials(active.other_display_name)}</div><div className={`message-bubble${message.sender_id === user?.id ? ' own-message' : ''}`}><p>{message.body}</p><small>{messageTime(message.created_at)}{message.sender_id === user?.id && message.read_at ? ' · Read' : ''}</small></div></article>) : <div className="message-empty"><MessageCircle size={24} /><h3>Start the conversation</h3><p>Send a private message to {active.other_display_name}.</p></div>}
          </div>
          <form className="message-compose" onSubmit={(event) => void submitMessage(event)}><label className="sr-only" htmlFor="private-message">Write a message</label><textarea id="private-message" maxLength={4000} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Type your message…" required /><button className="button button-primary" aria-label="Send" disabled={sending || !draft.trim()}><Send size={17} /></button><small className="compose-limit">{draft.length}/4000</small></form>
        </> : <div className="message-empty"><MessageCircle size={28} /><h2>Select a conversation</h2><p>{user?.role === 'farmer' ? 'Choose Contacts to start a private conversation with an eligible CropPulse reviewer.' : 'Your private conversation history will appear here.'}</p></div>}
      </section>

      <aside className="panel conversation-details" aria-label="About this conversation">
        <h2><ShieldCheck size={17} /> About this conversation</h2>
        {active ? <>
          <div className="details-person"><div className="message-avatar">{initials(active.other_display_name)}</div><div><strong>{active.other_display_name}</strong><small>{active.other_role}</small></div></div>
          {activeReviewer && <div className="details-row"><span>Eligible district</span><strong>{activeReviewer.eligible_districts.join(', ')}</strong></div>}
          <div className="details-status"><i /> Current participant access</div>
          <hr />
          <h3>Conversation details</h3>
          <dl><div><dt>Started</dt><dd>{dateTime(active.created_at)}</dd></div><div><dt>Messages</dt><dd>{total}</dd></div><div><dt>Unread</dt><dd>{active.unread_count}</dd></div></dl>
        </> : <div className="details-empty"><UserRound size={21} /><p>Participant details and message counts appear here when you select a conversation.</p></div>}
        <div className="details-footnote"><ShieldCheck size={15} /><p>{unreadTotal ? `${unreadTotal} unread message${unreadTotal === 1 ? '' : 's'} across your conversations.` : 'Unread counts update when new messages arrive.'}</p></div>
      </aside>
    </div>}
  </>;
}
