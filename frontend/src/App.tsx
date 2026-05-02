import { useState } from "react";
import { ScopeModal } from "./components/ScopeModal";
import { ChatWindow } from "./components/ChatWindow";
import { useConversation } from "./hooks/useConversation";
import type { DocumentScope } from "./types";

export default function App() {
  const {
    active,
    startConversation,
    addMessage,
    updateMessage,
    setFeedback,
  } = useConversation();

  const [showScopeModal, setShowScopeModal] = useState(!active);

  function handleStart(scope: DocumentScope) {
    startConversation(scope);
    setShowScopeModal(false);
  }

  function handleNewConversation() {
    setShowScopeModal(true);
  }

  return (
    <div className="flex h-dvh flex-col bg-gray-100">
      {/* New conversation button */}
      {active && !showScopeModal && (
        <div className="absolute right-4 top-3 z-10">
          <button
            onClick={handleNewConversation}
            className="min-h-[44px] rounded-lg bg-white px-3 py-2 text-xs font-medium text-gray-600 shadow-sm ring-1 ring-gray-200 hover:bg-gray-50"
          >
            New chat
          </button>
        </div>
      )}

      {showScopeModal && <ScopeModal onStart={handleStart} />}

      {active && (
        <ChatWindow
          conversation={active}
          onAddMessage={addMessage}
          onUpdateMessage={updateMessage}
          onFeedback={setFeedback}
        />
      )}
    </div>
  );
}
