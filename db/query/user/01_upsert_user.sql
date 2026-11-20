-- 회원 등록·수정 (email 이 같으면 수정)
-- 바꿀 값: 아래 SET 줄
SET @user_name = '홍길동', @gender = 'male', @birth_date = '1995-03-01', @email = 'hong@example.com';

INSERT INTO body.users (user_name, gender, birth_date, email)
VALUES (@user_name, @gender, @birth_date, @email) AS new
ON DUPLICATE KEY UPDATE user_name = new.user_name, gender = new.gender, birth_date = new.birth_date;

SELECT user_id, user_name, gender, birth_date, email, created_at, updated_at
FROM body.users WHERE email = @email;
