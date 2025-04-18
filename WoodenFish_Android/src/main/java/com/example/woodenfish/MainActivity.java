package com.example.woodenfish;

import android.content.Context;
import android.content.SharedPreferences;
import android.media.MediaPlayer;
import android.os.Bundle;
import android.view.View;
import android.view.animation.ScaleAnimation;
import android.widget.ImageButton;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {
    private TextView counterTextView;
    private ImageButton woodenFishButton;
    private int counter = 0;
    private SharedPreferences sharedPreferences;
    private MediaPlayer mediaPlayer;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        counterTextView = findViewById(R.id.counterTextView);
        woodenFishButton = findViewById(R.id.woodenFishButton);

        sharedPreferences = getSharedPreferences("CounterPrefs", Context.MODE_PRIVATE);
        counter = sharedPreferences.getInt("counter", 0);
        counterTextView.setText(String.valueOf(counter));

        mediaPlayer = MediaPlayer.create(this, R.raw.tap_sound);

        woodenFishButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                counter++;
                counterTextView.setText(String.valueOf(counter));

                ScaleAnimation scaleAnimation = new ScaleAnimation(1f, 0.9f, 1f, 0.9f, ScaleAnimation.RELATIVE_TO_SELF, 0.5f, ScaleAnimation.RELATIVE_TO_SELF, 0.5f);
                scaleAnimation.setDuration(100);
                scaleAnimation.setRepeatCount(1);
                scaleAnimation.setRepeatMode(ScaleAnimation.REVERSE);
                woodenFishButton.startAnimation(scaleAnimation);

                mediaPlayer.start();

                SharedPreferences.Editor editor = sharedPreferences.edit();
                editor.putInt("counter", counter);
                editor.apply();
            }
        });
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (mediaPlayer != null) {
            mediaPlayer.release();
            mediaPlayer = null;
        }
    }
}