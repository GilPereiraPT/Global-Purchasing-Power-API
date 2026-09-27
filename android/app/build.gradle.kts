plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    namespace = "com.earnwage.app"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.earnwage.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 4
        versionName = "0.7.1"
        buildConfigField("String", "API_BASE_URL", "\"https://earnwage-api.policlinicosdesantoandre.com\"")
    }
    buildTypes {
        getByName("release") {
            // Internal testing only: optimized release signed with the Android debug key.
            // Use the production upload keystore before any Play Store submission.
            signingConfig = signingConfigs.getByName("debug")
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
        }
    }
    buildFeatures { compose = true; buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
    packaging { resources { excludes += "/META-INF/{AL2.0,LGPL2.1}" } }
}
dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.ui:ui")
}
