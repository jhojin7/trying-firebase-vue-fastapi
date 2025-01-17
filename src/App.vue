<template>
  <div class="container mx-auto px-4 py-8">
    <div v-if="!isAuthenticated">
      <h1 class="text-3xl font-bold mb-4">Todo App</h1>
      <div class="space-y-4">
        <button @click="signInWithGoogle" class="bg-red-500 text-white px-4 py-2 rounded">
          Sign in with Google
        </button>
        <button @click="signInWithApple" class="bg-black text-white px-4 py-2 rounded block">
          Sign in with Apple
        </button>
        <div class="border p-4 rounded">
          <input v-model="email" type="email" placeholder="Email" class="border p-2 w-full mb-2">
          <input v-model="password" type="password" placeholder="Password" class="border p-2 w-full mb-2">
          <button @click="signInWithEmail" class="bg-blue-500 text-white px-4 py-2 rounded">
            Sign in
          </button>
        </div>
      </div>
    </div>

    <div v-else>
      <div class="flex justify-between items-center mb-4">
        <h1 class="text-3xl font-bold">My Todos</h1>
        <button @click="signOut" class="bg-red-500 text-white px-4 py-2 rounded">
          Sign Out
        </button>
      </div>

      <div class="mb-4">
        <input v-model="newTodo" @keyup.enter="addTodo" type="text" placeholder="Add new todo"
          class="border p-2 w-full">
      </div>

      <ul class="space-y-2">
        <li v-for="todo in todos" :key="todo.id" class="flex items-center justify-between border p-2">
          <div class="flex items-center">
            <input type="checkbox" :checked="todo.completed" @change="toggleTodo(todo.id)" class="mr-2">
            <span :class="{ 'line-through': todo.completed }">{{ todo.text }}</span>
          </div>
          <button @click="deleteTodo(todo.id)" class="text-red-500">Delete</button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { initializeApp } from 'firebase/app'
import {
  getAuth,
  signInWithPopup,
  GoogleAuthProvider,
  OAuthProvider,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut
} from 'firebase/auth'

// Firebase configuration
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID
};

// Initialize Firebase
const app = initializeApp(firebaseConfig)
const auth = getAuth(app)

// Auth state
const isAuthenticated = ref(false)
const email = ref('')
const password = ref('')

// Todo state
const todos = ref([])
const newTodo = ref('')

// API URL
const API_URL = 'http://localhost:9090/api'

// Auth functions
const signInWithGoogle = async () => {
  try {
    const provider = new GoogleAuthProvider()
    await signInWithPopup(auth, provider)
    isAuthenticated.value = true
    loadTodos()
  } catch (error) {
    console.error('Google sign in error:', error)
  }
}

const signInWithApple = async () => {
  try {
    const provider = new OAuthProvider('apple.com')
    await signInWithPopup(auth, provider)
    isAuthenticated.value = true
    loadTodos()
  } catch (error) {
    console.error('Apple sign in error:', error)
  }
}

const signInWithEmail = async () => {
  try {
    await signInWithEmailAndPassword(auth, email.value, password.value)
    isAuthenticated.value = true
    loadTodos()
  } catch (error) {
    console.error('Email sign in error:', error)
  }
}

const signOut = async () => {
  try {
    await firebaseSignOut(auth)
    isAuthenticated.value = false
    todos.value = []
  } catch (error) {
    console.error('Sign out error:', error)
  }
}

// Todo functions
const loadTodos = async () => {
  const token = await auth.currentUser.getIdToken()
  const response = await fetch(`${API_URL}/todos`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  todos.value = await response.json()
}

const addTodo = async () => {
  if (!newTodo.value.trim()) return

  const token = await auth.currentUser.getIdToken()
  const response = await fetch(`${API_URL}/todos`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text: newTodo.value,
      completed: false
    })
  })

  const todo = await response.json()
  todos.value.push(todo)
  newTodo.value = ''
}

const toggleTodo = async (id) => {
  const todo = todos.value.find(t => t.id === id)
  const token = await auth.currentUser.getIdToken()

  await fetch(`${API_URL}/todos/${id}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      completed: !todo.completed
    })
  })

  todo.completed = !todo.completed
}

const deleteTodo = async (id) => {
  const token = await auth.currentUser.getIdToken()
  await fetch(`${API_URL}/todos/${id}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })

  todos.value = todos.value.filter(t => t.id !== id)
}

// Auth listener
onMounted(() => {
  auth.onAuthStateChanged(user => {
    isAuthenticated.value = !!user
    if (user) {
      loadTodos()
    }
  })
})
</script>